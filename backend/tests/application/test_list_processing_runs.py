from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from types import TracebackType

import pytest

from supervisor_ai.application import (
    ProcessingRunCursorPosition,
    ProcessingRunListRecord,
)
from supervisor_ai.application.use_cases import (
    ListProcessingRunsQuery,
    ListProcessingRunsUseCase,
)

NOW = datetime(2026, 7, 23, 14, tzinfo=UTC)


def run_record(index: int) -> ProcessingRunListRecord:
    return ProcessingRunListRecord(
        processing_run_id=f"run-{index}",
        event_id=f"event-{index}",
        source="csv-example",
        external_reference=f"external-{index}",
        started_at=NOW,
        completed_at=NOW,
        final_status="posted",
        rules_engine_version="rules-1",
    )


class RepositoryFake:
    def __init__(
        self,
        records: tuple[ProcessingRunListRecord, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.received: dict[str, object] | None = None

    def search(self, **filters: object) -> tuple[ProcessingRunListRecord, ...]:
        self.received = filters
        if self.error is not None:
            raise self.error
        return self.records


class UnitOfWorkFake:
    def __init__(self, repository: RepositoryFake) -> None:
        self.processing_runs = repository
        self.closed = False
        self.rolled_back = False
        self.commits = 0

    def __enter__(self) -> "UnitOfWorkFake":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        self.closed = True
        self.rolled_back = exc_type is not None

    def commit(self) -> None:
        self.commits += 1


def execute(
    query: ListProcessingRunsQuery | None = None,
    records: tuple[ProcessingRunListRecord, ...] = (),
    error: Exception | None = None,
):
    repository = RepositoryFake(records, error)
    unit_of_work = UnitOfWorkFake(repository)
    result = ListProcessingRunsUseCase(lambda: unit_of_work).execute(
        query or ListProcessingRunsQuery()
    )
    return result, repository, unit_of_work


def test_default_query_empty_result_is_read_only() -> None:
    result, repository, unit_of_work = execute()
    assert result.items == ()
    assert result.next_cursor_position is None
    assert repository.received == {
        "source": None,
        "external_reference": None,
        "final_status": None,
        "rules_engine_version": None,
        "start_date": None,
        "end_date": None,
        "after": None,
        "limit": 51,
    }
    assert unit_of_work.closed and not unit_of_work.rolled_back
    assert unit_of_work.commits == 0


def test_forwards_filters_and_cursor() -> None:
    after = ProcessingRunCursorPosition(NOW, "run-cursor")
    query = ListProcessingRunsQuery(
        source="csv-example",
        external_reference="external-1",
        final_status="posted",
        rules_engine_version="rules-1",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        limit=20,
        after=after,
    )
    _, repository, _ = execute(query)
    assert repository.received == {
        "source": "csv-example",
        "external_reference": "external-1",
        "final_status": "posted",
        "rules_engine_version": "rules-1",
        "start_date": date(2026, 7, 1),
        "end_date": date(2026, 7, 31),
        "after": after,
        "limit": 21,
    }


def test_limit_plus_one_builds_cursor_from_last_returned_item() -> None:
    result, _, _ = execute(
        ListProcessingRunsQuery(limit=2),
        (run_record(3), run_record(2), run_record(1)),
    )
    assert [item.processing_run_id for item in result.items] == ["run-3", "run-2"]
    assert result.next_cursor_position == ProcessingRunCursorPosition(NOW, "run-2")


def test_final_page_has_no_cursor_and_preserves_order() -> None:
    result, _, _ = execute(
        ListProcessingRunsQuery(limit=2),
        (run_record(2), run_record(1)),
    )
    assert [item.processing_run_id for item in result.items] == ["run-2", "run-1"]
    assert result.next_cursor_position is None


@pytest.mark.parametrize("limit", [1, 50, 100])
def test_valid_limits(limit: int) -> None:
    assert ListProcessingRunsQuery(limit=limit).limit == limit


@pytest.mark.parametrize("limit", [0, 101])
def test_invalid_limits(limit: int) -> None:
    with pytest.raises(ValueError, match="limit"):
        ListProcessingRunsQuery(limit=limit)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", ""),
        ("source", " "),
        ("source", "x" * 101),
        ("external_reference", ""),
        ("external_reference", "x" * 256),
        ("final_status", ""),
        ("final_status", "x" * 101),
        ("rules_engine_version", ""),
        ("rules_engine_version", "x" * 101),
    ],
)
def test_invalid_text_filters(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        ListProcessingRunsQuery(**{field: value})


def test_inverted_interval_is_invalid() -> None:
    with pytest.raises(ValueError, match="start_date"):
        ListProcessingRunsQuery(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 7, 31),
        )


def test_contracts_are_immutable() -> None:
    query = ListProcessingRunsQuery()
    with pytest.raises(FrozenInstanceError):
        query.limit = 1


def test_repository_error_rolls_back_and_closes() -> None:
    repository = RepositoryFake(error=RuntimeError("database failed"))
    unit_of_work = UnitOfWorkFake(repository)
    with pytest.raises(RuntimeError, match="database failed"):
        ListProcessingRunsUseCase(lambda: unit_of_work).execute(
            ListProcessingRunsQuery()
        )
    assert unit_of_work.closed and unit_of_work.rolled_back
    assert unit_of_work.commits == 0
