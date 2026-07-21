from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import get_type_hints

import pytest

from supervisor_ai.rules_engine import (
    CommercialEventType,
    Currency,
    NonLoyaltyAdditionalType,
    PaymentValidationResult,
    PaymentValidationStatus,
    RemunerationAmountEvaluator,
    RemunerationAmountInput,
    RemunerationAmountReason,
    RemunerationAmountResult,
    RemunerationAmountStatus,
    RemunerationCalculationMethod,
)


def payment_result(
    status: PaymentValidationStatus = PaymentValidationStatus.VALIDATED,
    *,
    event_id: str = "event:1",
) -> PaymentValidationResult:
    return PaymentValidationResult(
        status=status,
        reasons=(),
        event_id=event_id,
        invoice_id="invoice:1",
        eligibility_conclusion_ids=("eligibility:1",),
        financial_reference_ids=("financial:1",),
        deadline_date=date(2026, 2, 14),
        validated_at=datetime(2026, 1, 10, tzinfo=UTC),
    )


def plan_input(**changes: object) -> RemunerationAmountInput:
    data = RemunerationAmountInput(
        event_id="event:1",
        payment_validation_result=payment_result(),
        payment_validation_reference="payment-validation:event:1",
        commercial_event_type=CommercialEventType.PLAN_UPGRADE,
        previous_recurring_amount=Decimal("99.90"),
        new_recurring_amount=Decimal("119.90"),
        full_new_plan_amount=Decimal("119.90"),
        renews_loyalty=True,
        commercial_reference_ids=("commercial:plan",),
        calculation_reference_ids=("amount:new-plan",),
    )
    return replace(data, **changes)


def additional_input(
    additional_type: NonLoyaltyAdditionalType,
    **changes: object,
) -> RemunerationAmountInput:
    data = RemunerationAmountInput(
        event_id="event:1",
        payment_validation_result=payment_result(),
        payment_validation_reference="payment-validation:event:1",
        commercial_event_type=CommercialEventType.NON_LOYALTY_ADDITIONAL,
        previous_recurring_amount=Decimal("99.90"),
        new_recurring_amount=Decimal("119.90"),
        additional_type=additional_type,
        renews_loyalty=False,
        commercial_reference_ids=("commercial:additional",),
        calculation_reference_ids=("amount:previous", "amount:new"),
    )
    return replace(data, **changes)


def evaluate(data: RemunerationAmountInput) -> RemunerationAmountResult:
    return RemunerationAmountEvaluator().evaluate(data)


def test_plan_upgrade_uses_full_new_monthly_amount() -> None:
    result = evaluate(plan_input())

    assert result.status is RemunerationAmountStatus.CALCULATED
    assert result.remuneration_amount == Decimal("119.90")
    assert result.calculation_method is (
        RemunerationCalculationMethod.FULL_NEW_PLAN_AMOUNT
    )
    assert result.currency is Currency.BRL


def test_proportional_invoice_amount_does_not_change_plan_remuneration() -> None:
    payment = replace(
        payment_result(),
        financial_reference_ids=("invoice-proportional:117.66",),
    )

    result = evaluate(plan_input(payment_validation_result=payment))

    assert result.remuneration_amount == Decimal("119.90")
    assert result.reasons == (
        RemunerationAmountReason.PAYMENT_VALIDATED,
        RemunerationAmountReason.FULL_NEW_PLAN_AMOUNT_USED,
    )


def test_mesh_uses_full_new_plan_amount() -> None:
    result = evaluate(
        plan_input(commercial_event_type=CommercialEventType.MESH_UPGRADE)
    )

    assert result.status is RemunerationAmountStatus.CALCULATED
    assert result.remuneration_amount == Decimal("119.90")
    assert result.calculation_method is (
        RemunerationCalculationMethod.FULL_NEW_PLAN_AMOUNT
    )


@pytest.mark.parametrize(
    "additional_type",
    [
        NonLoyaltyAdditionalType.WATCH_TV,
        NonLoyaltyAdditionalType.PUBLIC_IP,
        NonLoyaltyAdditionalType.CAMERA,
    ],
)
def test_non_loyalty_additional_uses_only_recurring_difference(
    additional_type: NonLoyaltyAdditionalType,
) -> None:
    result = evaluate(additional_input(additional_type))

    assert result.status is RemunerationAmountStatus.CALCULATED
    assert result.remuneration_amount == Decimal("20.00")
    assert result.calculation_method is (
        RemunerationCalculationMethod.RECURRING_AMOUNT_DIFFERENCE
    )


@pytest.mark.parametrize("new_amount", [Decimal("99.90"), Decimal("89.90")])
def test_non_positive_difference_is_not_applicable(new_amount: Decimal) -> None:
    result = evaluate(
        additional_input(
            NonLoyaltyAdditionalType.PUBLIC_IP,
            new_recurring_amount=new_amount,
        )
    )

    assert result.status is RemunerationAmountStatus.NOT_APPLICABLE
    assert result.remuneration_amount is None
    assert result.reasons[-1] is (
        RemunerationAmountReason.NON_POSITIVE_REMUNERATION
    )


def test_missing_full_plan_amount_is_not_evaluable() -> None:
    result = evaluate(plan_input(full_new_plan_amount=None))

    assert result.status is RemunerationAmountStatus.NOT_EVALUABLE
    assert result.reasons[-1] is RemunerationAmountReason.MISSING_FULL_PLAN_AMOUNT


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("previous_recurring_amount", RemunerationAmountReason.MISSING_PREVIOUS_AMOUNT),
        ("new_recurring_amount", RemunerationAmountReason.MISSING_NEW_AMOUNT),
    ],
)
def test_missing_additional_amount_is_not_evaluable(
    field: str, reason: RemunerationAmountReason
) -> None:
    result = evaluate(
        additional_input(NonLoyaltyAdditionalType.WATCH_TV, **{field: None})
    )

    assert result.status is RemunerationAmountStatus.NOT_EVALUABLE
    assert result.reasons[-1] is reason


@pytest.mark.parametrize(
    ("payment_status", "expected_status", "reason"),
    [
        (
            PaymentValidationStatus.EXPIRED,
            RemunerationAmountStatus.NOT_APPLICABLE,
            RemunerationAmountReason.PAYMENT_NOT_VALIDATED,
        ),
        (
            PaymentValidationStatus.PENDING_PAYMENT,
            RemunerationAmountStatus.NOT_APPLICABLE,
            RemunerationAmountReason.PAYMENT_NOT_VALIDATED,
        ),
        (
            PaymentValidationStatus.NOT_EVALUABLE,
            RemunerationAmountStatus.NOT_EVALUABLE,
            RemunerationAmountReason.PAYMENT_NOT_VALIDATED,
        ),
        (
            PaymentValidationStatus.PENDING_MANUAL_REVIEW,
            RemunerationAmountStatus.PENDING_MANUAL_REVIEW,
            RemunerationAmountReason.PAYMENT_PENDING_MANUAL_REVIEW,
        ),
    ],
)
def test_payment_validation_status_is_respected(
    payment_status: PaymentValidationStatus,
    expected_status: RemunerationAmountStatus,
    reason: RemunerationAmountReason,
) -> None:
    result = evaluate(
        plan_input(payment_validation_result=payment_result(payment_status))
    )

    assert result.status is expected_status
    assert result.reasons == (reason,)


@pytest.mark.parametrize(
    "event_type",
    [
        CommercialEventType.DOWNGRADE,
        CommercialEventType.UNSUPPORTED_COMMERCIAL_EVENT,
    ],
)
def test_unsupported_or_downgrade_event_is_not_applicable(
    event_type: CommercialEventType,
) -> None:
    result = evaluate(
        plan_input(
            commercial_event_type=event_type,
            renews_loyalty=None,
        )
    )

    assert result.status is RemunerationAmountStatus.NOT_APPLICABLE
    assert result.reasons[-1] is (
        RemunerationAmountReason.UNSUPPORTED_COMMERCIAL_EVENT
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"has_commercial_classification_conflict": True},
        {"renews_loyalty": False},
    ],
)
def test_commercial_classification_conflict_requires_review(
    changes: dict[str, object],
) -> None:
    result = evaluate(plan_input(**changes))

    assert result.status is RemunerationAmountStatus.PENDING_MANUAL_REVIEW
    assert result.reasons[-1] is (
        RemunerationAmountReason.COMMERCIAL_CLASSIFICATION_CONFLICT
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"has_inconsistent_input": True},
        {"full_new_plan_amount": Decimal("NaN")},
        {"full_new_plan_amount": 119.90},
        {"event_id": "other-event"},
    ],
)
def test_inconsistent_input_is_not_evaluable(
    changes: dict[str, object],
) -> None:
    result = evaluate(plan_input(**changes))

    assert result.status is RemunerationAmountStatus.NOT_EVALUABLE
    assert result.reasons == (RemunerationAmountReason.INCONSISTENT_INPUT,)


def test_evaluation_is_deterministic_and_does_not_mutate_input() -> None:
    data = plan_input(
        commercial_reference_ids=("commercial:b", "commercial:a"),
        calculation_reference_ids=("amount:b", "amount:a"),
    )
    snapshot = deepcopy(data)
    evaluator = RemunerationAmountEvaluator()

    first = evaluator.evaluate(data)
    second = evaluator.evaluate(data)

    assert first == second
    assert data == snapshot
    assert first.commercial_reference_ids == ("commercial:a", "commercial:b")
    assert first.calculation_reference_ids == ("amount:a", "amount:b")


def test_contracts_are_immutable_and_money_does_not_allow_float() -> None:
    data = plan_input()
    result = evaluate(data)
    hints = get_type_hints(RemunerationAmountInput)

    assert "float" not in str(hints["previous_recurring_amount"])
    assert "float" not in str(hints["new_recurring_amount"])
    assert "float" not in str(hints["full_new_plan_amount"])
    with pytest.raises(AttributeError):
        data.event_id = "other"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        result.status = RemunerationAmountStatus.NOT_APPLICABLE  # type: ignore[misc]
