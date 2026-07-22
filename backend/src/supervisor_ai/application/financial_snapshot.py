from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from supervisor_ai.rules_engine import (
    InvoicePaymentStatus,
    NonLoyaltyAdditionalType,
)


def _validate_datetime(value: datetime | None, field_name: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field_name} must be timezone-aware")


def _validate_money(value: Decimal | None, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field_name} must be a finite Decimal")
    if value < Decimal("0"):
        raise ValueError(f"{field_name} must not be negative")


@dataclass(frozen=True, slots=True)
class PaymentFacts:
    evaluated_at: datetime
    invoice_id: str | None
    invoice_due_date: date | None
    invoice_paid_at: datetime | None
    invoice_status: InvoicePaymentStatus | None
    invoice_recurring_amount: Decimal | None
    expected_recurring_amount: Decimal | None
    invoice_linked_to_event: bool | None
    is_first_new_value_invoice: bool | None
    first_invoice_candidate_count: int | None
    already_validated_event_ids: tuple[str, ...] = ()
    financial_reference_ids: tuple[str, ...] = ()
    has_link_conflict: bool = False
    has_duplicate_invoice_event_link: bool = False
    has_inconsistent_financial_input: bool = False

    def __post_init__(self) -> None:
        _validate_datetime(self.evaluated_at, "evaluated_at")
        _validate_datetime(self.invoice_paid_at, "invoice_paid_at")
        _validate_money(self.invoice_recurring_amount, "invoice_recurring_amount")
        _validate_money(
            self.expected_recurring_amount, "expected_recurring_amount"
        )
        if (
            self.first_invoice_candidate_count is not None
            and self.first_invoice_candidate_count < 0
        ):
            raise ValueError("first_invoice_candidate_count must not be negative")


@dataclass(frozen=True, slots=True)
class RemunerationFacts:
    payment_validation_reference: str
    previous_recurring_amount: Decimal | None = None
    new_recurring_amount: Decimal | None = None
    full_new_plan_amount: Decimal | None = None
    additional_type: NonLoyaltyAdditionalType | None = None
    renews_loyalty: bool | None = None
    commercial_reference_ids: tuple[str, ...] = ()
    calculation_reference_ids: tuple[str, ...] = ()
    has_commercial_classification_conflict: bool = False
    has_inconsistent_input: bool = False

    def __post_init__(self) -> None:
        if not self.payment_validation_reference:
            raise ValueError("payment_validation_reference must not be empty")
        _validate_money(self.previous_recurring_amount, "previous_recurring_amount")
        _validate_money(self.new_recurring_amount, "new_recurring_amount")
        _validate_money(self.full_new_plan_amount, "full_new_plan_amount")


@dataclass(frozen=True, slots=True)
class RemunerationPostingFacts:
    beneficiary_id: str | None
    posted_at: datetime | None
    posting_reference: str | None
    source_reference_ids: tuple[str, ...]
    remuneration_calculation_reference: str | None
    has_ledger_reference_conflict: bool = False
    has_inconsistent_input: bool = False

    def __post_init__(self) -> None:
        _validate_datetime(self.posted_at, "posted_at")


@dataclass(frozen=True, slots=True)
class FinancialSnapshot:
    payment: PaymentFacts
    remuneration: RemunerationFacts
    posting: RemunerationPostingFacts
