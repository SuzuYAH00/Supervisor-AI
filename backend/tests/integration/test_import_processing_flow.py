from datetime import UTC, datetime

from supervisor_ai.import_engine import RawRecord, ReadResult, SourceMetadata
from supervisor_ai.processing_engine import (
    TechnicalNormalizationProcessor,
    build_processing_contexts,
    process_batch,
)


def make_read_result(records: list[RawRecord]) -> ReadResult:
    return ReadResult(
        records=records,
        metadata=SourceMetadata(
            source_name="integration-source",
            read_at=datetime(2026, 7, 17, tzinfo=UTC),
            attributes={"resource": "integration-test"},
        ),
    )


def test_empty_read_result_flows_to_empty_batch_result() -> None:
    read_result = make_read_result([])

    contexts = build_processing_contexts(read_result)
    batch_result = process_batch(TechnicalNormalizationProcessor(), contexts)

    assert contexts == []
    assert batch_result.processed == []
    assert batch_result.rejected == []


def test_single_record_preserves_origin_across_complete_flow() -> None:
    raw_record = RawRecord(data={"name": "  Ana  "})
    read_result = make_read_result([raw_record])

    contexts = build_processing_contexts(read_result)
    batch_result = process_batch(TechnicalNormalizationProcessor(), contexts)

    assert len(contexts) == 1
    assert batch_result.processed[0].data == {"name": "Ana"}
    assert batch_result.processed[0].origin is contexts[0]
    assert contexts[0].raw_record is raw_record
    assert contexts[0].source_metadata is read_result.metadata


def test_multiple_records_preserve_order_and_receive_distinct_trace_ids() -> None:
    records = [
        RawRecord(data={"position": 1, "value": " first "}),
        RawRecord(data={"position": 2, "value": " second "}),
        RawRecord(data={"position": 3, "value": " third "}),
    ]
    read_result = make_read_result(records)

    contexts = build_processing_contexts(read_result)
    batch_result = process_batch(TechnicalNormalizationProcessor(), contexts)

    assert [context.raw_record for context in contexts] == records
    assert [record.data["position"] for record in batch_result.processed] == [
        1,
        2,
        3,
    ]
    assert [record.data["value"] for record in batch_result.processed] == [
        "first",
        "second",
        "third",
    ]
    assert len({context.trace_id for context in contexts}) == len(contexts)


def test_nested_structures_are_normalized_without_mutating_raw_data() -> None:
    raw_data = {
        "items": [" first ", {"label": " value ", "empty": "  "}],
        "details": {"nested": [" second "]},
    }
    raw_record = RawRecord(data=raw_data)
    read_result = make_read_result([raw_record])

    contexts = build_processing_contexts(read_result)
    batch_result = process_batch(TechnicalNormalizationProcessor(), contexts)

    assert batch_result.processed[0].data == {
        "items": ["first", {"label": "value", "empty": None}],
        "details": {"nested": ["second"]},
    }
    assert raw_record.data == {
        "items": [" first ", {"label": " value ", "empty": "  "}],
        "details": {"nested": [" second "]},
    }
