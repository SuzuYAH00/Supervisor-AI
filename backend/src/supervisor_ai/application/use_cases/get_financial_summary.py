from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.application.use_cases.get_financial_snapshot import (
    GetFinancialSnapshotQuery,
)
from supervisor_ai.rules_engine import Currency, LedgerEntry

GetFinancialSummaryQuery = GetFinancialSnapshotQuery

_PERCENTAGE_SCALE = Decimal("0.01")
_ONE_HUNDRED = Decimal("100")


@dataclass(frozen=True, slots=True)
class FinancialSummaryCurrencyTotal:
    currency: Currency
    amount: Decimal


@dataclass(frozen=True, slots=True)
class CollaboratorCurrencySummary:
    currency: Currency
    amount: Decimal
    credit_count: int
    rank: int
    share_percentage: Decimal


@dataclass(frozen=True, slots=True)
class CollaboratorFinancialSummary:
    collaborator_id: str
    credit_count: int
    totals_by_currency: tuple[CollaboratorCurrencySummary, ...]


@dataclass(frozen=True, slots=True)
class GetFinancialSummaryResult:
    filters: GetFinancialSummaryQuery
    collaborator_count: int
    credit_count: int
    totals_by_currency: tuple[FinancialSummaryCurrencyTotal, ...]
    collaborators: tuple[CollaboratorFinancialSummary, ...]


@dataclass(frozen=True, slots=True)
class _Aggregate:
    amount: Decimal
    credit_count: int


class GetFinancialSummaryUseCase:
    """Agrega créditos persistidos sem recalcular qualquer remuneração."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: GetFinancialSummaryQuery) -> GetFinancialSummaryResult:
        with self._unit_of_work_factory() as unit_of_work:
            entries = unit_of_work.ledger.find_credits(
                beneficiary_id=query.collaborator_id,
                start_date=query.start_date,
                end_date=query.end_date,
            )
        return _summarize(query, entries)


def _summarize(
    query: GetFinancialSummaryQuery,
    entries: tuple[LedgerEntry, ...],
) -> GetFinancialSummaryResult:
    aggregates: dict[tuple[str, Currency], _Aggregate] = {}
    collaborator_counts: dict[str, int] = {}
    currency_totals: dict[Currency, Decimal] = {}
    for entry in entries:
        key = (entry.beneficiary_id, entry.currency)
        current = aggregates.get(key, _Aggregate(Decimal("0"), 0))
        aggregates[key] = _Aggregate(
            amount=current.amount + entry.amount,
            credit_count=current.credit_count + 1,
        )
        collaborator_counts[entry.beneficiary_id] = (
            collaborator_counts.get(entry.beneficiary_id, 0) + 1
        )
        currency_totals[entry.currency] = (
            currency_totals.get(entry.currency, Decimal("0")) + entry.amount
        )

    rankings = _rank_by_currency(aggregates)
    collaborators = tuple(
        CollaboratorFinancialSummary(
            collaborator_id=collaborator_id,
            credit_count=collaborator_counts[collaborator_id],
            totals_by_currency=tuple(
                CollaboratorCurrencySummary(
                    currency=currency,
                    amount=aggregate.amount,
                    credit_count=aggregate.credit_count,
                    rank=rankings[(collaborator_id, currency)],
                    share_percentage=_share(
                        aggregate.amount, currency_totals[currency]
                    ),
                )
                for (owner, currency), aggregate in sorted(
                    aggregates.items(), key=lambda item: item[0][1].value
                )
                if owner == collaborator_id
            ),
        )
        for collaborator_id in sorted(collaborator_counts)
    )
    totals = tuple(
        FinancialSummaryCurrencyTotal(currency, amount)
        for currency, amount in sorted(
            currency_totals.items(), key=lambda item: item[0].value
        )
    )
    return GetFinancialSummaryResult(
        filters=query,
        collaborator_count=len(collaborators),
        credit_count=len(entries),
        totals_by_currency=totals,
        collaborators=collaborators,
    )


def _rank_by_currency(
    aggregates: dict[tuple[str, Currency], _Aggregate],
) -> dict[tuple[str, Currency], int]:
    rankings: dict[tuple[str, Currency], int] = {}
    currencies = sorted(
        {currency for _, currency in aggregates}, key=lambda currency: currency.value
    )
    for currency in currencies:
        ordered = sorted(
            (
                (collaborator_id, aggregate)
                for (collaborator_id, item_currency), aggregate in aggregates.items()
                if item_currency is currency
            ),
            key=lambda item: (
                -item[1].amount,
                -item[1].credit_count,
                item[0],
            ),
        )
        for position, (collaborator_id, _) in enumerate(ordered, start=1):
            rankings[(collaborator_id, currency)] = position
    return rankings


def _share(amount: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return Decimal("0.00")
    return ((amount / total) * _ONE_HUNDRED).quantize(
        _PERCENTAGE_SCALE,
        rounding=ROUND_HALF_UP,
    )
