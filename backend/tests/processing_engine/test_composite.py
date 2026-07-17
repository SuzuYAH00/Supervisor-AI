from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from supervisor_ai.import_engine import RawRecord, SourceMetadata
from supervisor_ai.processing_engine import (
    CompositeProcessor,
    ImportedRecordContext,
    ProcessedRecord,
    ProcessingError,
    Processor,
    RecordRejection,
    process_batch,
)


def make_record() -> ProcessedRecord:
    context = ImportedRecordContext(
        raw_record=RawRecord(data={"value": "start"}),
        source_metadata=SourceMetadata(
            source_name="test-source",
            read_at=datetime(2026, 7, 17, tzinfo=UTC),
        ),
    )
    return ProcessedRecord(origin=context, data={"value": "start"})


class TransformProcessor:
    def __init__(
        self,
        name: str,
        transform: Callable[[dict], dict],
        calls: list[str],
    ) -> None:
        self.name = name
        self.transform = transform
        self.calls = calls
        self.received: list[dict] = []

    def process(self, record: ProcessedRecord) -> ProcessedRecord:
        self.calls.append(self.name)
        self.received.append(record.data)
        return ProcessedRecord(
            origin=record.origin,
            data=self.transform(dict(record.data)),
        )


class RejectingProcessor:
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def process(self, record: ProcessedRecord) -> RecordRejection:
        self.calls.append(self.name)
        return RecordRejection(
            origin=record.origin,
            reason_code="rejected",
            message="Expected technical rejection.",
        )


class FailingProcessor:
    def __init__(self, error: ProcessingError) -> None:
        self.error = error

    def process(self, record: ProcessedRecord) -> ProcessedRecord:
        raise self.error


def add_field(name: str, value: str) -> Callable[[dict], dict]:
    def transform(data: dict) -> dict:
        data[name] = value
        return data

    return transform


def test_executes_two_processors_in_order_and_passes_first_output() -> None:
    calls: list[str] = []
    first = TransformProcessor("first", add_field("first", "done"), calls)
    second = TransformProcessor("second", add_field("second", "done"), calls)

    result = CompositeProcessor([first, second]).process(make_record())

    assert calls == ["first", "second"]
    assert second.received == [{"value": "start", "first": "done"}]
    assert result.data == {
        "value": "start",
        "first": "done",
        "second": "done",
    }


def test_three_processors_accumulate_transformations() -> None:
    calls: list[str] = []
    processors = [
        TransformProcessor("one", add_field("one", "1"), calls),
        TransformProcessor("two", add_field("two", "2"), calls),
        TransformProcessor("three", add_field("three", "3"), calls),
    ]

    result = CompositeProcessor(processors).process(make_record())

    assert calls == ["one", "two", "three"]
    assert result.data == {
        "value": "start",
        "one": "1",
        "two": "2",
        "three": "3",
    }


def test_rejection_in_first_step_stops_later_steps() -> None:
    calls: list[str] = []
    later = TransformProcessor("later", add_field("later", "done"), calls)

    result = CompositeProcessor(
        [RejectingProcessor("reject", calls), later]
    ).process(make_record())

    assert isinstance(result, RecordRejection)
    assert calls == ["reject"]


def test_rejection_in_intermediate_step_stops_later_steps() -> None:
    calls: list[str] = []
    processors: list[Processor] = [
        TransformProcessor("first", add_field("first", "done"), calls),
        RejectingProcessor("reject", calls),
        TransformProcessor("later", add_field("later", "done"), calls),
    ]

    result = CompositeProcessor(processors).process(make_record())

    assert isinstance(result, RecordRejection)
    assert calls == ["first", "reject"]


def test_propagates_processing_error_unchanged() -> None:
    expected = ProcessingError("processing unavailable")

    with pytest.raises(ProcessingError) as caught:
        CompositeProcessor([FailingProcessor(expected)]).process(make_record())

    assert caught.value is expected


def test_preserves_origin_and_trace_id_through_chain() -> None:
    record = make_record()
    trace_id = record.origin.trace_id
    composite = CompositeProcessor(
        [
            TransformProcessor("first", add_field("first", "done"), []),
            TransformProcessor("second", add_field("second", "done"), []),
        ]
    )

    result = composite.process(record)

    assert result.origin is record.origin
    assert result.origin.trace_id is trace_id


def test_rejects_empty_processor_chain() -> None:
    with pytest.raises(ValueError, match="requires at least one processor"):
        CompositeProcessor([])


def test_composite_implements_processor_structurally() -> None:
    composite = CompositeProcessor(
        [TransformProcessor("only", lambda data: data, [])]
    )

    assert isinstance(composite, Processor)


def test_process_batch_executes_composite_processor() -> None:
    record = make_record()
    composite = CompositeProcessor(
        [
            TransformProcessor("first", add_field("first", "done"), []),
            TransformProcessor("second", add_field("second", "done"), []),
        ]
    )

    result = process_batch(composite, [record.origin])

    assert result.processed[0].origin is record.origin
    assert result.processed[0].data == {
        "value": "start",
        "first": "done",
        "second": "done",
    }
