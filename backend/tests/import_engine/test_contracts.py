from datetime import UTC, datetime

from supervisor_ai.import_engine import (
    Connector,
    RawRecord,
    ReadResult,
    SourceMetadata,
    SourceReadError,
)


class StubConnector:
    def __init__(self, result: ReadResult) -> None:
        self._result = result

    def read(self) -> ReadResult:
        return self._result


def test_connector_accepts_structural_implementation() -> None:
    metadata = SourceMetadata(
        source_name="stub",
        read_at=datetime(2026, 7, 16, tzinfo=UTC),
    )
    expected = ReadResult(
        records=[RawRecord(external_id="record-1", data={"value": 10})],
        metadata=metadata,
    )
    connector = StubConnector(expected)

    assert isinstance(connector, Connector)
    assert connector.read() == expected


def test_read_result_supports_nested_raw_values_and_source_metadata() -> None:
    metadata = SourceMetadata(
        source_name="generic-source",
        read_at=datetime(2026, 7, 16, tzinfo=UTC),
        cursor="next-page",
        attributes={"resource": "events"},
    )
    record = RawRecord(
        external_id="event-42",
        data={
            "active": True,
            "details": {"score": 9.5},
            "tags": ["new", None],
        },
        metadata={"line": 42, "file": "events.source"},
    )

    result = ReadResult(records=[record], metadata=metadata)

    assert result.records == [record]
    assert result.metadata == metadata
    assert result.records[0].metadata == {
        "line": 42,
        "file": "events.source",
    }


def test_contract_values_are_explicitly_mutable() -> None:
    record = RawRecord(data={"value": 1})

    record.external_id = "changed"
    record.data["value"] = 2
    record.metadata["offset"] = 10

    assert record.external_id == "changed"
    assert record.data == {"value": 2}
    assert record.metadata == {"offset": 10}


def test_read_result_represents_successful_empty_read() -> None:
    metadata = SourceMetadata(
        source_name="empty-source",
        read_at=datetime(2026, 7, 16, tzinfo=UTC),
    )

    result = ReadResult(records=[], metadata=metadata)

    assert result.records == []
    assert result.metadata == metadata


def test_source_read_error_exposes_failure_context() -> None:
    error = SourceReadError(
        source_name="generic-source",
        message="source unavailable",
        retryable=True,
    )

    assert str(error) == "generic-source: source unavailable"
    assert error.source_name == "generic-source"
    assert error.message == "source unavailable"
    assert error.retryable is True
    assert error.args == ("source unavailable",)


def test_source_read_error_is_not_retryable_by_default() -> None:
    error = SourceReadError(
        source_name="generic-source",
        message="invalid source data",
    )

    assert error.retryable is False
