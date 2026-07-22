from collections.abc import Callable
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from supervisor_ai.application import (
    FinancialSnapshot,
    PaymentFacts,
    RemunerationFacts,
    RemunerationPostingFacts,
)
from supervisor_ai.rules_engine import InvoicePaymentStatus

NOW = datetime(2026, 7, 21, tzinfo=UTC)


def payment() -> PaymentFacts:
    return PaymentFacts(
        evaluated_at=NOW,
        invoice_id="invoice-1",
        invoice_due_date=date(2026, 7, 20),
        invoice_paid_at=NOW,
        invoice_status=InvoicePaymentStatus.PAID,
        invoice_recurring_amount=Decimal("99.90"),
        expected_recurring_amount=Decimal("99.90"),
        invoice_linked_to_event=True,
        is_first_new_value_invoice=True,
        first_invoice_candidate_count=1,
    )


def remuneration() -> RemunerationFacts:
    return RemunerationFacts(
        payment_validation_reference="payment-1",
        full_new_plan_amount=Decimal("99.90"),
        renews_loyalty=True,
    )


def posting() -> RemunerationPostingFacts:
    return RemunerationPostingFacts(
        beneficiary_id="employee-1",
        posted_at=NOW,
        posting_reference="posting-1",
        source_reference_ids=("invoice-1",),
        remuneration_calculation_reference="calculation-1",
    )


def test_constructs_immutable_snapshot_and_preserves_decimal() -> None:
    snapshot = FinancialSnapshot(payment(), remuneration(), posting())
    assert snapshot.payment.invoice_recurring_amount == Decimal("99.90")
    assert isinstance(snapshot.payment.invoice_recurring_amount, Decimal)
    field_name = "invoice_id"
    with pytest.raises(FrozenInstanceError):
        setattr(snapshot.payment, field_name, "changed")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PaymentFacts(
            evaluated_at=datetime(2026, 7, 21),
            invoice_id=None,
            invoice_due_date=None,
            invoice_paid_at=None,
            invoice_status=None,
            invoice_recurring_amount=None,
            expected_recurring_amount=None,
            invoice_linked_to_event=None,
            is_first_new_value_invoice=None,
            first_invoice_candidate_count=None,
        ),
        lambda: RemunerationPostingFacts(
            beneficiary_id=None,
            posted_at=datetime(2026, 7, 21),
            posting_reference=None,
            source_reference_ids=(),
            remuneration_calculation_reference=None,
        ),
    ],
)
def test_rejects_naive_financial_datetimes(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        factory()


def test_rejects_negative_money_according_to_existing_invariant() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        RemunerationFacts(
            payment_validation_reference="payment-1",
            full_new_plan_amount=Decimal("-0.01"),
        )


def test_partial_snapshot_preserves_absence() -> None:
    partial = FinancialSnapshot(
        payment=PaymentFacts(
            evaluated_at=NOW,
            invoice_id=None,
            invoice_due_date=None,
            invoice_paid_at=None,
            invoice_status=None,
            invoice_recurring_amount=None,
            expected_recurring_amount=None,
            invoice_linked_to_event=None,
            is_first_new_value_invoice=None,
            first_invoice_candidate_count=None,
        ),
        remuneration=RemunerationFacts(
            payment_validation_reference="payment-1",
        ),
        posting=RemunerationPostingFacts(
            beneficiary_id=None,
            posted_at=None,
            posting_reference=None,
            source_reference_ids=(),
            remuneration_calculation_reference=None,
        ),
    )
    assert partial.payment.invoice_id is None
    assert partial.remuneration.full_new_plan_amount is None
    assert partial.posting.posted_at is None
