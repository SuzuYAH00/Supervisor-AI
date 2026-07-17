from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

import supervisor_ai.processing_engine as processing_engine
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
        self.received: list[ProcessedRecord] = []

    def process(self, record: ProcessedRecord) -> ProcessedRecord:
        self.received.append(record)
        return ProcessedRecord(
            origin=record.origin,
            data=dict(record.data),
            metadata={"processor": "copy"},
        )


class RejectInvalidProcessor:
    def process(self, record: ProcessedRecord) -> ProcessedRecord | RecordRejection:
        if record.data.get("valid") is not True:
            return RecordRejection(
                origin=record.origin,
                reason_code="invalid_record",
                message="Record did not pass technical validation.",
            )
        return ProcessedRecord(origin=record.origin, data=dict(record.data))


class FailingProcessor:
    def __init__(self, error: ProcessingError) -> None:
        self.error = error
        self.received: list[ProcessedRecord] = []

    def process(self, record: ProcessedRecord) -> ProcessedRecord:
        self.received.append(record)
        if len(self.received) == 2:
            raise self.error
        return ProcessedRecord(origin=record.origin, data={"visited": True})


class MutatingProcessor:
    def process(self, record: ProcessedRecord) -> ProcessedRecord:
        nested = record.data["nested"]
        assert isinstance(nested, dict)
        items = nested["items"]
        assert isinstance(items, list)
        items.append("changed")
        return record


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
    assert isinstance(make_context(1).trace_id, UUID)


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


def test_process_batch_creates_initial_processed_record() -> None:
    context = make_context(1)
    processor = CopyProcessor()

    result = process_batch(processor, [context])

    initial_record = processor.received[0]
    assert isinstance(initial_record, ProcessedRecord)
    assert initial_record.origin is context
    assert initial_record.origin.trace_id is context.trace_id
    assert initial_record.data == context.raw_record.data
    assert result.processed[0].origin is context


def test_process_batch_deep_copies_raw_data_before_processing() -> None:
    raw_data = {"nested": {"items": ["original"]}}
    context = ImportedRecordContext(
        raw_record=RawRecord(data=raw_data),
        source_metadata=SourceMetadata(
            source_name="test-source",
            read_at=datetime(2026, 7, 16, tzinfo=UTC),
        ),
    )

    result = process_batch(MutatingProcessor(), [context])

    assert result.processed[0].data == {"nested": {"items": ["original", "changed"]}}
    assert context.raw_record.data == {"nested": {"items": ["original"]}}
    assert result.processed[0].data is not context.raw_record.data
    assert result.processed[0].data["nested"] is not raw_data["nested"]


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
    assert processor.received == []


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


def test_partial_rejection_does_not_discard_valid_records() -> None:
    contexts = [make_context(1), make_context(2, valid=False), make_context(3)]

    result = process_batch(RejectInvalidProcessor(), contexts)

    assert [record.origin for record in result.processed] == [contexts[0], contexts[2]]
    assert result.rejected[0].origin is contexts[1]
    assert result.rejected[0].reason_code == "invalid_record"


def test_technical_failure_stops_batch_and_is_propagated_unchanged() -> None:
    expected = ProcessingError("processing unavailable")
    processor = FailingProcessor(expected)
    contexts = [make_context(1), make_context(2), make_context(3)]

    with pytest.raises(ProcessingError) as caught:
        process_batch(processor, contexts)

    assert caught.value is expected
    assert [record.origin for record in processor.received] == contexts[:2]


def test_accepts_structural_processor_without_inheritance() -> None:
    processor = CopyProcessor()

    assert isinstance(processor, Processor)
    assert len(process_batch(processor, [make_context(1)]).processed) == 1


def test_processing_subject_is_not_part_of_public_api() -> None:
    assert not hasattr(processing_engine, "ProcessingSubject")
    assert "ProcessingSubject" not in processing_engine.__all__
