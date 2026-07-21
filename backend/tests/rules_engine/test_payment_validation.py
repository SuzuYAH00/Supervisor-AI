from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import get_type_hints

import pytest

from supervisor_ai.rules_engine import (
    InvoicePaymentStatus,
    PaymentValidationEvaluator,
    PaymentValidationInput,
    PaymentValidationReason,
    PaymentValidationResult,
    PaymentValidationStatus,
    RemunerationEligibilityResult,
    RemunerationEligibilityStatus,
)

DUE_DATE = date(2026, 1, 10)
PAID_AT = datetime(2026, 1, 10, 12, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 1, 10, 15, tzinfo=UTC)


def eligibility(
    status: RemunerationEligibilityStatus = (
        RemunerationEligibilityStatus.POTENTIALLY_ELIGIBLE
    ),
) -> RemunerationEligibilityResult:
    return RemunerationEligibilityResult(
        status=status,
        reasons=(),
        commercial_conclusion_ids=("commercial.upgrade",),
        operational_conclusion_ids=("operational.eligible",),
    )


def valid_input(**changes: object) -> PaymentValidationInput:
    data = PaymentValidationInput(
        event_id="event:1",
        eligibility_result=eligibility(),
        evaluated_at=EVALUATED_AT,
        invoice_id="invoice:10",
        invoice_due_date=DUE_DATE,
        invoice_paid_at=PAID_AT,
        invoice_status=InvoicePaymentStatus.PAID,
        invoice_recurring_amount=Decimal("99.90"),
        expected_recurring_amount=Decimal("99.90"),
        invoice_linked_to_event=True,
        is_first_new_value_invoice=True,
        first_invoice_candidate_count=1,
        financial_reference_ids=("financial.payment", "financial.invoice"),
    )
    return replace(data, **changes)


def evaluate(data: PaymentValidationInput) -> PaymentValidationResult:
    return PaymentValidationEvaluator().evaluate(data)


@pytest.mark.parametrize("days_after_due", [0, 35])
def test_payment_inside_deadline_is_validated(days_after_due: int) -> None:
    paid_at = datetime.combine(
        DUE_DATE + timedelta(days=days_after_due),
        datetime.min.time(),
        tzinfo=UTC,
    )

    result = evaluate(valid_input(invoice_paid_at=paid_at))

    assert result.status is PaymentValidationStatus.VALIDATED
    assert result.reasons == (PaymentValidationReason.PAYMENT_WITHIN_DEADLINE,)
    assert result.deadline_date == DUE_DATE + timedelta(days=35)
    assert result.validated_at == paid_at


def test_payment_on_day_36_is_expired() -> None:
    paid_at = datetime.combine(
        DUE_DATE + timedelta(days=36),
        datetime.min.time(),
        tzinfo=UTC,
    )

    result = evaluate(valid_input(invoice_paid_at=paid_at))

    assert result.status is PaymentValidationStatus.EXPIRED
    assert result.reasons == (PaymentValidationReason.PAYMENT_AFTER_DEADLINE,)


def test_unpaid_invoice_inside_deadline_is_pending() -> None:
    result = evaluate(
        valid_input(
            invoice_status=InvoicePaymentStatus.UNPAID,
            invoice_paid_at=None,
            evaluated_at=datetime(2026, 2, 14, tzinfo=UTC),
        )
    )

    assert result.status is PaymentValidationStatus.PENDING_PAYMENT
    assert result.reasons == (PaymentValidationReason.INVOICE_NOT_PAID,)


def test_unpaid_invoice_after_deadline_is_expired() -> None:
    result = evaluate(
        valid_input(
            invoice_status=InvoicePaymentStatus.UNPAID,
            invoice_paid_at=None,
            evaluated_at=datetime(2026, 2, 15, tzinfo=UTC),
        )
    )

    assert result.status is PaymentValidationStatus.EXPIRED
    assert result.reasons == (
        PaymentValidationReason.INVOICE_NOT_PAID,
        PaymentValidationReason.PAYMENT_AFTER_DEADLINE,
    )


@pytest.mark.parametrize(
    ("eligibility_status", "expected_status", "reason"),
    [
        (
            RemunerationEligibilityStatus.NOT_ELIGIBLE,
            PaymentValidationStatus.NOT_ELIGIBLE,
            PaymentValidationReason.ELIGIBILITY_NOT_APPROVED,
        ),
        (
            RemunerationEligibilityStatus.NOT_EVALUABLE,
            PaymentValidationStatus.NOT_EVALUABLE,
            PaymentValidationReason.ELIGIBILITY_NOT_APPROVED,
        ),
        (
            RemunerationEligibilityStatus.PENDING_MANUAL_REVIEW,
            PaymentValidationStatus.PENDING_MANUAL_REVIEW,
            PaymentValidationReason.ELIGIBILITY_PENDING_REVIEW,
        ),
    ],
)
def test_phase_d_status_is_respected(
    eligibility_status: RemunerationEligibilityStatus,
    expected_status: PaymentValidationStatus,
    reason: PaymentValidationReason,
) -> None:
    result = evaluate(valid_input(eligibility_result=eligibility(eligibility_status)))

    assert result.status is expected_status
    assert result.reasons == (reason,)


def test_already_validated_event_returns_idempotent_validation() -> None:
    result = evaluate(
        valid_input(
            already_validated_event_ids=("event:1",),
            invoice_due_date=None,
        )
    )

    assert result.status is PaymentValidationStatus.VALIDATED
    assert result.reasons == (PaymentValidationReason.EVENT_ALREADY_VALIDATED,)
    assert result.validated_at is None


def test_same_invoice_can_validate_distinct_events() -> None:
    first = evaluate(valid_input(event_id="event:1"))
    second = evaluate(valid_input(event_id="event:2"))

    assert first.status is PaymentValidationStatus.VALIDATED
    assert second.status is PaymentValidationStatus.VALIDATED
    assert first.invoice_id == second.invoice_id == "invoice:10"
    assert first.event_id != second.event_id


def test_second_attempt_for_same_event_does_not_create_new_validation() -> None:
    first = evaluate(valid_input())
    second = evaluate(valid_input(already_validated_event_ids=("event:1",)))

    assert first.reasons == (PaymentValidationReason.PAYMENT_WITHIN_DEADLINE,)
    assert second.reasons == (PaymentValidationReason.EVENT_ALREADY_VALIDATED,)


def test_invoice_not_linked_to_event_is_not_eligible() -> None:
    result = evaluate(valid_input(invoice_linked_to_event=False))

    assert result.status is PaymentValidationStatus.NOT_ELIGIBLE
    assert result.reasons == (
        PaymentValidationReason.INVOICE_NOT_LINKED_TO_EVENT,
    )


def test_first_invoice_not_identified_is_not_evaluable() -> None:
    result = evaluate(
        valid_input(
            is_first_new_value_invoice=False,
            first_invoice_candidate_count=0,
        )
    )

    assert result.status is PaymentValidationStatus.NOT_EVALUABLE
    assert result.reasons == (
        PaymentValidationReason.FIRST_NEW_VALUE_INVOICE_NOT_IDENTIFIED,
    )


def test_multiple_first_invoice_candidates_require_review() -> None:
    result = evaluate(valid_input(first_invoice_candidate_count=2))

    assert result.status is PaymentValidationStatus.PENDING_MANUAL_REVIEW
    assert result.reasons == (
        PaymentValidationReason.MULTIPLE_FIRST_INVOICE_CANDIDATES,
    )


def test_compatible_decimal_amount_is_used_without_conversion() -> None:
    data = valid_input()

    result = evaluate(data)

    assert result.status is PaymentValidationStatus.VALIDATED
    assert isinstance(data.invoice_recurring_amount, Decimal)


def test_amount_mismatch_requires_review() -> None:
    result = evaluate(valid_input(invoice_recurring_amount=Decimal("89.90")))

    assert result.status is PaymentValidationStatus.PENDING_MANUAL_REVIEW
    assert result.reasons == (PaymentValidationReason.INVOICE_AMOUNT_MISMATCH,)


def test_missing_due_date_is_not_evaluable() -> None:
    result = evaluate(valid_input(invoice_due_date=None))

    assert result.status is PaymentValidationStatus.NOT_EVALUABLE
    assert result.reasons == (PaymentValidationReason.MISSING_DUE_DATE,)


def test_paid_invoice_without_payment_date_is_not_evaluable() -> None:
    result = evaluate(valid_input(invoice_paid_at=None))

    assert result.status is PaymentValidationStatus.NOT_EVALUABLE
    assert result.reasons == (PaymentValidationReason.MISSING_PAYMENT_DATE,)


@pytest.mark.parametrize(
    "changes",
    [
        {"has_inconsistent_financial_input": True},
        {
            "invoice_status": InvoicePaymentStatus.UNPAID,
            "invoice_paid_at": PAID_AT,
        },
        {"evaluated_at": datetime(2026, 1, 10)},
        {"invoice_recurring_amount": 99.90},
        {"invoice_recurring_amount": Decimal("NaN")},
    ],
)
def test_inconsistent_financial_input_is_not_evaluable(
    changes: dict[str, object],
) -> None:
    result = evaluate(valid_input(**changes))

    assert result.status is PaymentValidationStatus.NOT_EVALUABLE
    assert result.reasons == (
        PaymentValidationReason.INCONSISTENT_FINANCIAL_INPUT,
    )


def test_link_conflicts_require_manual_review() -> None:
    conflict = evaluate(valid_input(has_link_conflict=True))
    duplicate = evaluate(valid_input(has_duplicate_invoice_event_link=True))

    assert conflict.status is PaymentValidationStatus.PENDING_MANUAL_REVIEW
    assert duplicate.reasons == (
        PaymentValidationReason.DUPLICATE_INVOICE_EVENT_LINK,
    )


def test_evaluation_is_deterministic_and_does_not_mutate_input() -> None:
    data = valid_input(
        already_validated_event_ids=("event:9", "event:8"),
        financial_reference_ids=("reference:b", "reference:a"),
    )
    snapshot = deepcopy(data)
    evaluator = PaymentValidationEvaluator()

    first = evaluator.evaluate(data)
    second = evaluator.evaluate(data)

    assert first == second
    assert data == snapshot
    assert first.financial_reference_ids == ("reference:a", "reference:b")


def test_contracts_are_immutable_and_money_does_not_allow_float() -> None:
    data = valid_input()
    result = evaluate(data)
    hints = get_type_hints(PaymentValidationInput)

    assert "float" not in str(hints["invoice_recurring_amount"])
    assert "float" not in str(hints["expected_recurring_amount"])
    with pytest.raises(AttributeError):
        data.invoice_id = "other"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        result.status = PaymentValidationStatus.EXPIRED  # type: ignore[misc]
