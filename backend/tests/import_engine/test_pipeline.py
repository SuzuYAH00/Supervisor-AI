from datetime import UTC, datetime

import pytest

import supervisor_ai.import_engine.pipeline as pipeline_module
from supervisor_ai.import_engine import (
    Connector,
    ImportPipeline,
    ReadResult,
    SourceMetadata,
    SourceReadError,
)


class StubConnector:
    def __init__(self, result: ReadResult) -> None:
        self.result = result
        self.read_count = 0

    def read(self) -> ReadResult:
        self.read_count += 1
        return self.result


class FailingConnector:
    def __init__(self, error: SourceReadError) -> None:
        self.error = error

    def read(self) -> ReadResult:
        raise self.error


def make_empty_result() -> ReadResult:
    return ReadResult(
        records=[],
        metadata=SourceMetadata(
            source_name="stub",
            read_at=datetime(2026, 7, 16, tzinfo=UTC),
        ),
    )


def test_runs_connector_once_and_returns_its_result() -> None:
    expected = make_empty_result()
    connector = StubConnector(expected)

    result = ImportPipeline(connector).run()

    assert result is expected
    assert connector.read_count == 1


def test_propagates_source_read_error_unchanged() -> None:
    expected = SourceReadError(
        source_name="stub",
        message="source unavailable",
        retryable=True,
    )

    with pytest.raises(SourceReadError) as caught:
        ImportPipeline(FailingConnector(expected)).run()

    assert caught.value is expected


def test_accepts_structural_connector_without_inheritance() -> None:
    connector = StubConnector(make_empty_result())

    assert isinstance(connector, Connector)
    assert ImportPipeline(connector).run() is connector.result


def test_pipeline_module_has_no_file_connector_dependency() -> None:
    assert "FileConnector" not in vars(pipeline_module)
