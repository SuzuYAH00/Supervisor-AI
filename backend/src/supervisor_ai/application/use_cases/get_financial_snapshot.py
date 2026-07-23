from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.rules_engine import Currency, LedgerEntryType


@dataclass(frozen=True, slots=True)
class GetFinancialSnapshotQuery:
    collaborator_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    def __post_init__(self) -> None:
        if self.collaborator_id == "":
            raise ValueError("collaborator_id must not be empty")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")


@dataclass(frozen=True, slots=True)
class FinancialSnapshotItem:
    ledger_entry_id: str
    commercial_event_id: str
    collaborator_id: str
    amount: Decimal
    currency: Currency
    posted_at: datetime
    entry_type: LedgerEntryType
    invoice_id: str | None


@dataclass(frozen=True, slots=True)
class FinancialSnapshotCurrencyTotal:
    currency: Currency
    amount: Decimal


@dataclass(frozen=True, slots=True)
class GetFinancialSnapshotResult:
    filters: GetFinancialSnapshotQuery
    credit_count: int
    totals_by_currency: tuple[FinancialSnapshotCurrencyTotal, ...]
    items: tuple[FinancialSnapshotItem, ...]


class GetFinancialSnapshotUseCase:
    """Projeta créditos persistidos sem recalcular qualquer remuneração."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: GetFinancialSnapshotQuery) -> GetFinancialSnapshotResult:
        with self._unit_of_work_factory() as unit_of_work:
            entries = unit_of_work.ledger.find_credits(
                beneficiary_id=query.collaborator_id,
                start_date=query.start_date,
                end_date=query.end_date,
            )
        items = tuple(
            FinancialSnapshotItem(
                ledger_entry_id=entry.entry_id,
                commercial_event_id=entry.event_id,
                collaborator_id=entry.beneficiary_id,
                amount=entry.amount,
                currency=entry.currency,
                posted_at=entry.posted_at,
                entry_type=entry.entry_type,
                invoice_id=entry.invoice_id,
            )
            for entry in entries
        )
        totals = tuple(
            FinancialSnapshotCurrencyTotal(
                currency=currency,
                amount=sum(
                    (item.amount for item in items if item.currency is currency),
                    start=Decimal("0"),
                ),
            )
            for currency in sorted({item.currency for item in items}, key=str)
        )
        return GetFinancialSnapshotResult(
            filters=query,
            credit_count=len(items),
            totals_by_currency=totals,
            items=items,
        )
