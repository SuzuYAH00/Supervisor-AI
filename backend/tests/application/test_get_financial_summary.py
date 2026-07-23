from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from types import TracebackType

import pytest

from supervisor_ai.application.use_cases import (
    GetFinancialSummaryQuery,
    GetFinancialSummaryUseCase,
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
        self.rolled_back = exc_type is not None
        self.closed = True

    def commit(self) -> None:
        self.commits += 1


def execute(
    entries: tuple[LedgerEntry, ...] = (),
    *,
    query: GetFinancialSummaryQuery | None = None,
    error: Exception | None = None,
):
    repository = LedgerRepositoryFake(entries, error)
    unit_of_work = UnitOfWorkFake(repository)
    result = GetFinancialSummaryUseCase(lambda: unit_of_work).execute(
        query or GetFinancialSummaryQuery()
    )
    return result, repository, unit_of_work


def entry(
    entry_id: str,
    collaborator_id: str,
    amount: str,
    currency: Currency = Currency.BRL,
) -> LedgerEntry:
    return replace(
        ledger_entry(entry_id, f"event-{entry_id}", amount=Decimal(amount)),
        beneficiary_id=collaborator_id,
        currency=currency,
        posted_at=datetime(2026, 7, 10, 12, tzinfo=UTC),
    )


def test_empty_summary_is_read_only_and_has_no_implicit_filters() -> None:
    result, repository, unit_of_work = execute()
    assert result.collaborator_count == result.credit_count == 0
    assert result.totals_by_currency == result.collaborators == ()
    assert repository.received_filters == (None, None, None)
    assert unit_of_work.closed and not unit_of_work.rolled_back
    assert unit_of_work.commits == 0


def test_aggregates_collaborators_currencies_counts_and_exact_amounts() -> None:
    entries = (
        entry("1", "alice", "100.00"),
        entry("2", "alice", "20.00"),
        entry("3", "alice", "7.50", Currency.USD),
        entry("4", "bob", "80.00"),
        entry("5", "bob", "2.50", Currency.USD),
    )
    original = tuple((item.entry_id, item.amount) for item in entries)
    result, _, _ = execute(entries)
    assert result.collaborator_count == 2
    assert result.credit_count == 5
    assert {item.currency: item.amount for item in result.totals_by_currency} == {
        Currency.BRL: Decimal("200.00"),
        Currency.USD: Decimal("10.00"),
    }
    alice, bob = result.collaborators
    assert (alice.collaborator_id, alice.credit_count) == ("alice", 3)
    assert (bob.collaborator_id, bob.credit_count) == ("bob", 2)
    assert [(item.currency, item.amount) for item in alice.totals_by_currency] == [
        (Currency.BRL, Decimal("120.00")),
        (Currency.USD, Decimal("7.50")),
    ]
    assert tuple((item.entry_id, item.amount) for item in entries) == original


def test_ranking_uses_amount_then_credit_count_then_collaborator_id() -> None:
    entries = (
        entry("1", "charlie", "50.00"),
        entry("2", "bob", "25.00"),
        entry("3", "bob", "25.00"),
        entry("4", "alice", "50.00"),
    )
    result, _, _ = execute(entries)
    ranks = {
        collaborator.collaborator_id: collaborator.totals_by_currency[0].rank
        for collaborator in result.collaborators
    }
    assert ranks == {"alice": 2, "bob": 1, "charlie": 3}


def test_percentages_use_decimal_round_half_up_with_two_places() -> None:
    result, _, _ = execute(
        (
            entry("1", "alice", "1.00"),
            entry("2", "bob", "2.00"),
            entry("3", "charlie", "5.00"),
        )
    )
    shares = {
        item.collaborator_id: item.totals_by_currency[0].share_percentage
        for item in result.collaborators
    }
    assert shares == {
        "alice": Decimal("12.50"),
        "bob": Decimal("25.00"),
        "charlie": Decimal("62.50"),
    }
    assert all(isinstance(value, Decimal) for value in shares.values())


def test_forwards_all_filters_to_repository() -> None:
    query = GetFinancialSummaryQuery(
        collaborator_id="alice",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )
    _, repository, _ = execute(query=query)
    assert repository.received_filters == (
        "alice",
        date(2026, 7, 1),
        date(2026, 7, 31),
    )


def test_repository_failure_rolls_back_context_without_commit() -> None:
    repository = LedgerRepositoryFake(error=RuntimeError("database failed"))
    unit_of_work = UnitOfWorkFake(repository)
    service = GetFinancialSummaryUseCase(lambda: unit_of_work)
    with pytest.raises(RuntimeError, match="database failed"):
        service.execute(GetFinancialSummaryQuery())
    assert unit_of_work.closed and unit_of_work.rolled_back
    assert unit_of_work.commits == 0
