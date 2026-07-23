from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import TracebackType

import pytest

from supervisor_ai.application import CommercialEventNotFound, ProcessingRun
from supervisor_ai.application.use_cases import (
    GetCommercialEventDetailsQuery,
    GetCommercialEventDetailsUseCase,
)
from supervisor_ai.rules_engine import LedgerEntry, LedgerEntryType
from tests.persistence.factories import (
    commercial_event,
    ledger_entry,
    processing_run,
)

NOW = datetime(2026, 7, 20, 12, tzinfo=UTC)


class EventRepositoryFake:
    def __init__(self, event_id: str | None = "event-1") -> None:
        self.event_id = event_id
        self.received_id: str | None = None

    def get_by_id(self, event_id: str):
        self.received_id = event_id
        return None if self.event_id is None else commercial_event(self.event_id)


class LedgerRepositoryFake:
    def __init__(self, entries: tuple[LedgerEntry, ...] = ()) -> None:
        self.entries = entries
        self.received_id: str | None = None

    def find_by_event_id(self, event_id: str) -> tuple[LedgerEntry, ...]:
        self.received_id = event_id
        return self.entries


class ProcessingRunRepositoryFake:
    def __init__(self, runs: tuple[ProcessingRun, ...] = ()) -> None:
        self.runs = runs
        self.received_id: str | None = None

    def find_by_event_id(self, event_id: str) -> tuple[ProcessingRun, ...]:
        self.received_id = event_id
        return self.runs


class UnitOfWorkFake:
    def __init__(
        self,
        events: EventRepositoryFake,
        ledger: LedgerRepositoryFake,
        processing_runs: ProcessingRunRepositoryFake,
        *,
        enter_error: Exception | None = None,
    ) -> None:
        self.events = events
        self.ledger = ledger
        self.processing_runs = processing_runs
        self.enter_error = enter_error
        self.closed = False
        self.rolled_back = False
        self.commits = 0

    def __enter__(self) -> "UnitOfWorkFake":
        if self.enter_error is not None:
            raise self.enter_error
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        self.rolled_back = exc_type is not None
        self.closed = True

    def commit(self) -> None:
        self.commits += 1


def test_query_rejects_blank_and_excessively_long_identifiers() -> None:
    for invalid in ("", "   ", "x" * 129):
        with pytest.raises(ValueError, match="commercial_event_id"):
            GetCommercialEventDetailsQuery(invalid)


def test_existing_event_without_related_records_returns_public_fields_only() -> None:
    events = EventRepositoryFake()
    ledger = LedgerRepositoryFake()
    runs = ProcessingRunRepositoryFake()
    unit_of_work = UnitOfWorkFake(events, ledger, runs)
    result = GetCommercialEventDetailsUseCase(lambda: unit_of_work).execute(
        GetCommercialEventDetailsQuery("event-1")
    )
    assert result.commercial_event.event_id == "event-1"
    assert result.commercial_event.external_reference == "external-1"
    assert result.ledger_entries == ()
    assert result.processing_runs == ()
    assert "raw_payload" not in {
        field.name for field in fields(result.commercial_event)
    }
    assert events.received_id == ledger.received_id == runs.received_id == "event-1"
    assert unit_of_work.closed and not unit_of_work.rolled_back
    assert unit_of_work.commits == 0


def test_not_found_raises_typed_error_without_related_queries() -> None:
    events = EventRepositoryFake(None)
    ledger = LedgerRepositoryFake()
    runs = ProcessingRunRepositoryFake()
    unit_of_work = UnitOfWorkFake(events, ledger, runs)
    service = GetCommercialEventDetailsUseCase(lambda: unit_of_work)
    with pytest.raises(CommercialEventNotFound):
        service.execute(GetCommercialEventDetailsQuery("missing"))
    assert events.received_id == "missing"
    assert ledger.received_id is None
    assert runs.received_id is None
    assert unit_of_work.closed and unit_of_work.rolled_back
    assert unit_of_work.commits == 0


def test_related_records_are_projected_and_sorted_without_mutation() -> None:
    later_entry = replace(
        ledger_entry("ledger-2", "event-1", amount=Decimal("20.10")),
        entry_type=LedgerEntryType.DEBIT,
        posted_at=NOW + timedelta(hours=2),
    )
    earlier_entry = replace(
        ledger_entry("ledger-1", "event-1", amount=Decimal("119.90")),
        posted_at=NOW + timedelta(hours=1),
    )
    later_run = replace(
        processing_run("run-2"),
        started_at=NOW + timedelta(hours=2),
        completed_at=NOW + timedelta(hours=3),
        created_at=NOW + timedelta(hours=2),
    )
    earlier_run = replace(
        processing_run("run-1"),
        started_at=NOW,
        completed_at=NOW + timedelta(minutes=1),
        created_at=NOW,
    )
    original_entries = (later_entry, earlier_entry)
    original_runs = (later_run, earlier_run)
    unit_of_work = UnitOfWorkFake(
        EventRepositoryFake(),
        LedgerRepositoryFake(original_entries),
        ProcessingRunRepositoryFake(original_runs),
    )
    result = GetCommercialEventDetailsUseCase(lambda: unit_of_work).execute(
        GetCommercialEventDetailsQuery("event-1")
    )
    assert tuple(item.ledger_entry_id for item in result.ledger_entries) == (
        "ledger-1",
        "ledger-2",
    )
    assert result.ledger_entries[0].amount == Decimal("119.90")
    assert result.ledger_entries[1].entry_type is LedgerEntryType.DEBIT
    assert tuple(item.processing_run_id for item in result.processing_runs) == (
        "run-1",
        "run-2",
    )
    assert (later_entry, earlier_entry) == original_entries
    assert (later_run, earlier_run) == original_runs


def test_unexpected_failure_closes_context_and_does_not_commit() -> None:
    class FailingEvents(EventRepositoryFake):
        def get_by_id(self, event_id: str):
            del event_id
            raise RuntimeError("database failed")

    unit_of_work = UnitOfWorkFake(
        FailingEvents(), LedgerRepositoryFake(), ProcessingRunRepositoryFake()
    )
    service = GetCommercialEventDetailsUseCase(lambda: unit_of_work)
    with pytest.raises(RuntimeError, match="database failed"):
        service.execute(GetCommercialEventDetailsQuery("event-1"))
    assert unit_of_work.closed and unit_of_work.rolled_back
    assert unit_of_work.commits == 0
