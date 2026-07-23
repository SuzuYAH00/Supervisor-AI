from dataclasses import FrozenInstanceError
from datetime import date
from types import TracebackType

import pytest

from supervisor_ai.application import ProcessingHealthCount, ProcessingHealthRecord
from supervisor_ai.application.use_cases import (
    GetProcessingHealthQuery,
    GetProcessingHealthUseCase,
)


class ProcessingHealthRepositoryFake:
    def __init__(
        self,
        record: ProcessingHealthRecord,
        error: Exception | None = None,
    ) -> None:
        self.record = record
        self.error = error
        self.received: tuple[object, ...] | None = None

    def get_processing_health(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
        rules_engine_version: str | None,
    ) -> ProcessingHealthRecord:
        self.received = (start_date, end_date, source, rules_engine_version)
        if self.error is not None:
            raise self.error
        return self.record


class UnitOfWorkFake:
    def __init__(self, repository: ProcessingHealthRepositoryFake) -> None:
        self.processing_health = repository
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


def record() -> ProcessingHealthRecord:
    return ProcessingHealthRecord(
        processing_run_total=3,
        by_final_status=(
            ProcessingHealthCount("posted", 2),
            ProcessingHealthCount("not_evaluable", 1),
        ),
        by_rules_engine_version=(
            ProcessingHealthCount("rules-2", 1),
            ProcessingHealthCount("rules-1", 2),
        ),
        events_with_processing_runs=2,
        events_without_processing_runs=1,
        events_with_multiple_processing_runs=1,
        events_with_ledger_entries=1,
        events_without_ledger_entries=2,
    )


def test_returns_factual_metrics_sorted_and_read_only() -> None:
    source_record = record()
    repository = ProcessingHealthRepositoryFake(source_record)
    unit_of_work = UnitOfWorkFake(repository)
    query = GetProcessingHealthQuery(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        source="csv-example",
        rules_engine_version="rules-1",
    )

    result = GetProcessingHealthUseCase(lambda: unit_of_work).execute(query)

    assert result.filters == query
    assert result.processing_runs.total == 3
    assert [item.value for item in result.processing_runs.by_final_status] == [
        "not_evaluable",
        "posted",
    ]
    assert [item.value for item in result.processing_runs.by_rules_engine_version] == [
        "rules-1",
        "rules-2",
    ]
    assert result.commercial_events.events_with_multiple_processing_runs == 1
    assert repository.received == (
        date(2026, 7, 1),
        date(2026, 7, 31),
        "csv-example",
        "rules-1",
    )
    assert repository.record is source_record
    assert unit_of_work.closed and not unit_of_work.rolled_back
    assert unit_of_work.commits == 0


def test_empty_result_and_default_filters() -> None:
    empty = ProcessingHealthRecord(0, (), (), 0, 0, 0, 0, 0)
    repository = ProcessingHealthRepositoryFake(empty)
    unit_of_work = UnitOfWorkFake(repository)
    result = GetProcessingHealthUseCase(lambda: unit_of_work).execute(
        GetProcessingHealthQuery()
    )
    assert result.processing_runs.total == 0
    assert result.processing_runs.by_final_status == ()
    assert repository.received == (None, None, None, None)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", ""),
        ("source", "   "),
        ("source", "x" * 101),
        ("rules_engine_version", ""),
        ("rules_engine_version", "   "),
        ("rules_engine_version", "x" * 101),
    ],
)
def test_rejects_invalid_text_filters(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        GetProcessingHealthQuery(**{field: value})


def test_rejects_inverted_interval() -> None:
    with pytest.raises(ValueError, match="start_date"):
        GetProcessingHealthQuery(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 7, 31),
        )


def test_contracts_are_immutable() -> None:
    query = GetProcessingHealthQuery()
    with pytest.raises(FrozenInstanceError):
        query.source = "changed"


def test_repository_failure_rolls_back_and_closes_without_commit() -> None:
    repository = ProcessingHealthRepositoryFake(
        record(),
        RuntimeError("database failed"),
    )
    unit_of_work = UnitOfWorkFake(repository)
    with pytest.raises(RuntimeError, match="database failed"):
        GetProcessingHealthUseCase(lambda: unit_of_work).execute(
            GetProcessingHealthQuery()
        )
    assert unit_of_work.closed and unit_of_work.rolled_back
    assert unit_of_work.commits == 0
