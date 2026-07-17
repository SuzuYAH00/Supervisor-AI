from datetime import UTC, datetime

import supervisor_ai.processing_engine as processing_engine
from supervisor_ai.import_engine import RawRecord, ReadResult, SourceMetadata
from supervisor_ai.processing_engine import build_processing_contexts


def make_read_result(records: list[RawRecord]) -> ReadResult:
    return ReadResult(
        records=records,
        metadata=SourceMetadata(
            source_name="test-source",
            read_at=datetime(2026, 7, 17, tzinfo=UTC),
            attributes={"file_name": "records.source"},
        ),
    )


def test_builds_no_contexts_for_empty_read_result() -> None:
    result = make_read_result([])

    contexts = build_processing_contexts(result)

    assert contexts == []


def test_builds_one_context_with_original_references() -> None:
    raw_record = RawRecord(
        data={"value": 1},
        metadata={"line_number": 2},
    )
    result = make_read_result([raw_record])

    contexts = build_processing_contexts(result)

    assert len(contexts) == 1
    assert contexts[0].raw_record is raw_record
    assert contexts[0].source_metadata is result.metadata


def test_preserves_record_order_and_shares_source_metadata() -> None:
    records = [
        RawRecord(data={"position": 1}),
        RawRecord(data={"position": 2}),
        RawRecord(data={"position": 3}),
    ]
    result = make_read_result(records)

    contexts = build_processing_contexts(result)

    assert [context.raw_record for context in contexts] == records
    assert all(context.source_metadata is result.metadata for context in contexts)


def test_generates_different_trace_id_for_each_context() -> None:
    result = make_read_result(
        [RawRecord(data={"value": 1}), RawRecord(data={"value": 2})]
    )

    contexts = build_processing_contexts(result)

    assert contexts[0].trace_id != contexts[1].trace_id


def test_does_not_mutate_read_result_or_its_internal_values() -> None:
    raw_record = RawRecord(
        data={"nested": {"value": 1}},
        metadata={"line_number": 2},
    )
    result = make_read_result([raw_record])
    original_records = result.records
    original_data = raw_record.data
    original_record_metadata = raw_record.metadata
    original_source_metadata = result.metadata
    original_source_attributes = result.metadata.attributes

    build_processing_contexts(result)

    assert result.records is original_records
    assert result.records[0] is raw_record
    assert raw_record.data is original_data
    assert raw_record.metadata is original_record_metadata
    assert result.metadata is original_source_metadata
    assert result.metadata.attributes is original_source_attributes


def test_function_is_available_in_public_processing_engine_api() -> None:
    assert processing_engine.build_processing_contexts is build_processing_contexts
    assert "build_processing_contexts" in processing_engine.__all__
