from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from supervisor_ai.import_engine import RawRecord, SourceMetadata
from supervisor_ai.processing_engine import (
    ImportedRecordContext,
    ProcessedRecord,
    ProcessingError,
    Processor,
    RecordRejection,
    process_batch,
)


class CopyProcessor:
    def __init__(self) -> None:
        self.processed_origins: list[ImportedRecordContext] = []

    def process(self, context: ImportedRecordContext) -> ProcessedRecord:
        self.processed_origins.append(context)
        return ProcessedRecord(
            origin=context,
            data=dict(context.raw_record.data),
            metadata={"processor": "copy"},
        )


class RejectInvalidProcessor:
    def process(
        self,
        context: ImportedRecordContext,
    ) -> ProcessedRecord | RecordRejection:
        if context.raw_record.data.get("valid") is not True:
            return RecordRejection(
                origin=context,
                reason_code="invalid_record",
                message="Record did not pass technical validation.",
            )
        return ProcessedRecord(
            origin=context,
            data=dict(context.raw_record.data),
        )


class FailingProcessor:
    def __init__(self, error: ProcessingError) -> None:
        self.error = error
        self.visited: list[ImportedRecordContext] = []

    def process(self, context: ImportedRecordContext) -> ProcessedRecord:
        self.visited.append(context)
        if len(self.visited) == 2:
            raise self.error
        return ProcessedRecord(origin=context, data={"visited": True})


def make_context(value: int, *, valid: bool = True) -> ImportedRecordContext:
    return ImportedRecordContext(
        raw_record=RawRecord(
            data={"value": value, "valid": valid},
            external_id=f"record-{value}",
            metadata={"line_number": value + 1},
        ),
        source_metadata=SourceMetadata(
            source_name="test-source",
            read_at=datetime(2026, 7, 16, tzinfo=UTC),
            attributes={"file_name": "records.source"},
        ),
    )


def test_imported_record_context_generates_trace_id() -> None:
    context = make_context(1)

    assert isinstance(context.trace_id, UUID)


def test_imported_record_context_accepts_explicit_trace_id() -> None:
    expected = uuid4()
    context = ImportedRecordContext(
        raw_record=RawRecord(data={}),
        source_metadata=SourceMetadata(
            source_name="test-source",
            read_at=datetime(2026, 7, 16, tzinfo=UTC),
        ),
        trace_id=expected,
    )

    assert context.trace_id is expected


def test_processes_successful_record_and_preserves_origin_instance() -> None:
    context = make_context(1)

    result = process_batch(CopyProcessor(), [context])

    assert len(result.processed) == 1
    assert result.processed[0].origin is context
    assert result.processed[0].data == {"value": 1, "valid": True}
    assert result.rejected == []


def test_processed_record_supports_normalized_standard_values() -> None:
    context = make_context(1)
    identifier = uuid4()
    processed_at = datetime(2026, 7, 16, 12, 30, tzinfo=UTC)
    processed = ProcessedRecord(
        origin=context,
        data={
            "amount": Decimal("10.50"),
            "date": date(2026, 7, 16),
            "processed_at": processed_at,
            "identifier": identifier,
            "nested": [{"amount": Decimal("1.25")}],
        },
    )

    assert processed.data["amount"] == Decimal("10.50")
    assert processed.data["date"] == date(2026, 7, 16)
    assert processed.data["processed_at"] is processed_at
    assert processed.data["identifier"] is identifier


def test_processes_empty_batch_without_calling_processor() -> None:
    processor = CopyProcessor()

    result = process_batch(processor, [])

    assert result.processed == []
    assert result.rejected == []
    assert processor.processed_origins == []


def test_preserves_order_separately_for_multiple_outcomes() -> None:
    contexts = [
        make_context(1),
        make_context(2, valid=False),
        make_context(3),
        make_context(4, valid=False),
    ]

    result = process_batch(RejectInvalidProcessor(), contexts)

    assert [record.origin for record in result.processed] == [contexts[0], contexts[2]]
    assert [rejection.origin for rejection in result.rejected] == [
        contexts[1],
        contexts[3],
    ]
    assert not hasattr(result, "outcomes")


def test_partial_rejection_does_not_discard_valid_records() -> None:
    valid_context = make_context(1)
    rejected_context = make_context(2, valid=False)
    another_valid_context = make_context(3)

    result = process_batch(
        RejectInvalidProcessor(),
        [valid_context, rejected_context, another_valid_context],
    )

    assert [record.origin for record in result.processed] == [
        valid_context,
        another_valid_context,
    ]
    assert len(result.rejected) == 1
    assert result.rejected[0].origin is rejected_context
    assert result.rejected[0].reason_code == "invalid_record"


def test_technical_failure_stops_batch_and_is_propagated_unchanged() -> None:
    expected = ProcessingError("processing unavailable")
    processor = FailingProcessor(expected)
    contexts = [make_context(1), make_context(2), make_context(3)]

    with pytest.raises(ProcessingError) as caught:
        process_batch(processor, contexts)

    assert caught.value is expected
    assert processor.visited == contexts[:2]


def test_accepts_structural_processor_without_inheritance() -> None:
    processor = CopyProcessor()

    assert isinstance(processor, Processor)
    assert len(process_batch(processor, [make_context(1)]).processed) == 1


def test_preserves_origin_traceability_for_both_outcomes() -> None:
    processed_context = make_context(1)
    rejected_context = make_context(2, valid=False)

    result = process_batch(
        RejectInvalidProcessor(),
        [processed_context, rejected_context],
    )

    assert result.processed[0].origin is processed_context
    assert result.processed[0].origin.raw_record.metadata == {"line_number": 2}
    assert result.processed[0].origin.source_metadata.source_name == "test-source"
    assert result.rejected[0].origin is rejected_context
    assert result.rejected[0].origin.source_metadata.attributes == {
        "file_name": "records.source"
    }
