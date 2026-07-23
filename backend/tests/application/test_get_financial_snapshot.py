from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from types import TracebackType

import pytest

from supervisor_ai.application.use_cases import (
    GetFinancialSnapshotQuery,
    GetFinancialSnapshotUseCase,
)
from supervisor_ai.rules_engine import Currency, LedgerEntry
from tests.persistence.factories import ledger_entry


class LedgerRepositoryFake:
    def __init__(
        self,
        entries: tuple[LedgerEntry, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.entries = entries
        self.error = error
        self.received_filters: tuple[object, ...] | None = None

    def find_credits(
        self,
        *,
        beneficiary_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[LedgerEntry, ...]:
        self.received_filters = (beneficiary_id, start_date, end_date)
        if self.error is not None:
            raise self.error
        return self.entries


class UnitOfWorkFake:
    def __init__(self, ledger: LedgerRepositoryFake) -> None:
        self.ledger = ledger
        self.entered = False
        self.closed = False
        self.rolled_back = False
        self.commits = 0

    def __enter__(self) -> "UnitOfWorkFake":
        self.entered = True
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


def use_case(
    entries: tuple[LedgerEntry, ...] = (), error: Exception | None = None
) -> tuple[GetFinancialSnapshotUseCase, LedgerRepositoryFake, UnitOfWorkFake]:
    repository = LedgerRepositoryFake(entries, error)
    unit_of_work = UnitOfWorkFake(repository)
    return GetFinancialSnapshotUseCase(lambda: unit_of_work), repository, unit_of_work


def test_returns_empty_snapshot_without_implicit_filters_or_commit() -> None:
    service, repository, unit_of_work = use_case()
    result = service.execute(GetFinancialSnapshotQuery())
    assert result.credit_count == 0
    assert result.totals_by_currency == ()
    assert result.items == ()
    assert repository.received_filters == (None, None, None)
    assert unit_of_work.entered and unit_of_work.closed
    assert unit_of_work.commits == 0
    assert unit_of_work.rolled_back is False


def test_forwards_filters_and_aggregates_exact_amounts_by_currency() -> None:
    first = ledger_entry("ledger-2", "event-2", amount=Decimal("119.90"))
    second = replace(
        ledger_entry("ledger-1", "event-1", amount=Decimal("20.10")),
        currency=Currency.USD,
        beneficiary_id="collaborator-1",
        posted_at=datetime(2026, 7, 10, 12, tzinfo=UTC),
    )
    service, repository, unit_of_work = use_case((second, first))
    query = GetFinancialSnapshotQuery(
        collaborator_id="collaborator-1",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )
    result = service.execute(query)
    assert repository.received_filters == (
        "collaborator-1",
        date(2026, 7, 1),
        date(2026, 7, 31),
    )
    assert result.credit_count == 2
    assert {total.currency: total.amount for total in result.totals_by_currency} == {
        Currency.BRL: Decimal("119.90"),
        Currency.USD: Decimal("20.10"),
    }
    assert tuple(item.ledger_entry_id for item in result.items) == (
        "ledger-1",
        "ledger-2",
    )
    assert unit_of_work.commits == 0


def test_query_rejects_empty_collaborator_and_inverted_interval() -> None:
    with pytest.raises(ValueError, match="collaborator_id"):
        GetFinancialSnapshotQuery(collaborator_id="")
    with pytest.raises(ValueError, match="start_date"):
        GetFinancialSnapshotQuery(
            start_date=date(2026, 8, 1), end_date=date(2026, 7, 31)
        )


def test_repository_failure_leaves_context_with_rollback_and_no_commit() -> None:
    service, _, unit_of_work = use_case(error=RuntimeError("database failed"))
    with pytest.raises(RuntimeError, match="database failed"):
        service.execute(GetFinancialSnapshotQuery())
    assert unit_of_work.closed is True
    assert unit_of_work.rolled_back is True
    assert unit_of_work.commits == 0
