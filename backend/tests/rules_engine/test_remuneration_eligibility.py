from copy import deepcopy

import pytest

from supervisor_ai.rules_engine import (
    CommercialClassificationName,
    ConclusionKind,
    ConclusionStatus,
    EvaluationConclusion,
    Justification,
    OperationalDecisionName,
    RemunerationEligibilityEvaluator,
    RemunerationEligibilityReason,
    RemunerationEligibilityResult,
    RemunerationEligibilityStatus,
)


def conclusion(
    name: str,
    *,
    status: ConclusionStatus = ConclusionStatus.TRUE,
    suffix: str = "1",
) -> EvaluationConclusion:
    return EvaluationConclusion(
        conclusion_id=f"conclusion.{name}.{suffix}",
        name=name,
        kind=ConclusionKind.DOMAIN_DECISION,
        status=status,
        justification=Justification(rule_id="previous-phase", summary="Result."),
    )


def eligible_inputs(
    commercial: CommercialClassificationName = (
        CommercialClassificationName.COMMERCIAL_UPGRADE
    ),
) -> tuple[EvaluationConclusion, ...]:
    return (
        conclusion(commercial),
        conclusion(OperationalDecisionName.TICKET_PRESENT),
        conclusion(OperationalDecisionName.SUPPORT_TICKET),
        conclusion(OperationalDecisionName.COMMERCIAL_AUTHOR_IDENTIFIED),
        conclusion(OperationalDecisionName.NO_DUPLICATE_AUTHOR),
        conclusion(OperationalDecisionName.PLAN_CHANGE_TICKET),
        conclusion(OperationalDecisionName.NON_ADMINISTRATIVE_CHANGE),
        conclusion(OperationalDecisionName.NON_CORRECTIVE_CHANGE),
        conclusion(OperationalDecisionName.NO_AUTHORSHIP_CONFLICT),
    )


def evaluate(
    conclusions: tuple[EvaluationConclusion, ...],
) -> RemunerationEligibilityResult:
    return RemunerationEligibilityEvaluator().evaluate(conclusions)


def replace(
    conclusions: tuple[EvaluationConclusion, ...],
    index: int,
    name: str,
    *,
    status: ConclusionStatus = ConclusionStatus.TRUE,
) -> tuple[EvaluationConclusion, ...]:
    changed = list(conclusions)
    changed[index] = conclusion(name, status=status)
    return tuple(changed)


def test_valid_upgrade_with_support_ticket_is_potentially_eligible() -> None:
    result = evaluate(eligible_inputs())

    assert result.status is RemunerationEligibilityStatus.POTENTIALLY_ELIGIBLE
    assert result.reasons == ()
    assert len(result.commercial_conclusion_ids) == 1
    assert len(result.operational_conclusion_ids) == 8


def test_valid_additional_sale_with_support_ticket_is_potentially_eligible() -> None:
    inputs = (
        *eligible_inputs(CommercialClassificationName.RECURRING_REVENUE_UNCHANGED),
        conclusion(CommercialClassificationName.COMMON_ADDITIONAL_SALE),
    )

    result = evaluate(inputs)

    assert result.status is RemunerationEligibilityStatus.POTENTIALLY_ELIGIBLE
    assert len(result.commercial_conclusion_ids) == 2


@pytest.mark.parametrize(
    ("index", "name", "reason"),
    [
        (
            0,
            CommercialClassificationName.COMMERCIAL_DOWNGRADE,
            RemunerationEligibilityReason.DOWNGRADE,
        ),
        (
            1,
            OperationalDecisionName.TICKET_MISSING,
            RemunerationEligibilityReason.NO_PLAN_CHANGE_TICKET,
        ),
        (
            2,
            OperationalDecisionName.NON_SUPPORT_TICKET,
            RemunerationEligibilityReason.TICKET_AUTHOR_NOT_SUPPORT,
        ),
        (
            5,
            OperationalDecisionName.NON_PLAN_CHANGE_TICKET,
            RemunerationEligibilityReason.NO_PLAN_CHANGE_TICKET,
        ),
        (
            6,
            OperationalDecisionName.ADMINISTRATIVE_CHANGE,
            RemunerationEligibilityReason.ADMINISTRATIVE_CHANGE,
        ),
        (
            7,
            OperationalDecisionName.CORRECTIVE_CHANGE,
            RemunerationEligibilityReason.CORRECTIVE_CHANGE,
        ),
    ],
)
def test_conclusive_ineligibility(index: int, name: str, reason: str) -> None:
    result = evaluate(replace(eligible_inputs(), index, name))

    assert result.status is RemunerationEligibilityStatus.NOT_ELIGIBLE
    assert reason in result.reasons


def test_event_without_commercial_nature_is_not_eligible() -> None:
    result = evaluate(
        eligible_inputs(CommercialClassificationName.RECURRING_REVENUE_UNCHANGED)
    )

    assert result.status is RemunerationEligibilityStatus.NOT_ELIGIBLE
    assert result.reasons == (RemunerationEligibilityReason.NO_COMMERCIAL_EVENT,)


def test_missing_ticket_author_is_not_evaluable() -> None:
    result = evaluate(
        replace(
            eligible_inputs(),
            3,
            OperationalDecisionName.COMMERCIAL_AUTHOR_MISSING,
        )
    )

    assert result.status is RemunerationEligibilityStatus.NOT_EVALUABLE
    assert result.reasons == (RemunerationEligibilityReason.MISSING_TICKET_AUTHOR,)


@pytest.mark.parametrize(
    ("index", "name", "reason"),
    [
        (
            3,
            OperationalDecisionName.COMMERCIAL_AUTHOR_IDENTIFIED,
            RemunerationEligibilityReason.DUPLICATE_CLAIM,
        ),
        (
            8,
            OperationalDecisionName.AUTHORSHIP_CONFLICT,
            RemunerationEligibilityReason.AUTHORSHIP_CONFLICT,
        ),
    ],
)
def test_authorship_review(index: int, name: str, reason: str) -> None:
    inputs = eligible_inputs()
    if reason is RemunerationEligibilityReason.DUPLICATE_CLAIM:
        inputs = replace(
            inputs,
            4,
            OperationalDecisionName.DUPLICATE_AUTHOR,
        )
    else:
        inputs = replace(inputs, index, name)

    result = evaluate(inputs)

    assert result.status is RemunerationEligibilityStatus.PENDING_MANUAL_REVIEW
    assert result.reasons == (reason,)


def test_insufficient_input_is_not_evaluable() -> None:
    inputs = tuple(
        item
        for item in eligible_inputs()
        if item.name != OperationalDecisionName.PLAN_CHANGE_TICKET
    )

    result = evaluate(inputs)

    assert result.status is RemunerationEligibilityStatus.NOT_EVALUABLE
    assert result.reasons == (RemunerationEligibilityReason.INSUFFICIENT_DATA,)


def test_explicit_not_evaluable_input_is_not_evaluable() -> None:
    inputs = replace(
        eligible_inputs(),
        5,
        OperationalDecisionName.TICKET_PURPOSE_NOT_EVALUABLE,
        status=ConclusionStatus.NOT_EVALUABLE,
    )

    result = evaluate(inputs)

    assert result.status is RemunerationEligibilityStatus.NOT_EVALUABLE
    assert result.reasons == (RemunerationEligibilityReason.INSUFFICIENT_DATA,)


def test_inconsistent_input_is_not_evaluable() -> None:
    inputs = (
        *eligible_inputs(),
        conclusion(OperationalDecisionName.TICKET_PRESENT, suffix="duplicate"),
    )

    result = evaluate(inputs)

    assert result.status is RemunerationEligibilityStatus.NOT_EVALUABLE
    assert result.reasons == (RemunerationEligibilityReason.INCONSISTENT_INPUT,)


def test_manual_review_precedes_conclusive_ineligibility() -> None:
    inputs = replace(
        eligible_inputs(),
        4,
        OperationalDecisionName.DUPLICATE_AUTHOR,
    )
    inputs = replace(
        inputs,
        6,
        OperationalDecisionName.ADMINISTRATIVE_CHANGE,
    )

    result = evaluate(inputs)

    assert result.status is RemunerationEligibilityStatus.PENDING_MANUAL_REVIEW
    assert result.reasons == (RemunerationEligibilityReason.DUPLICATE_CLAIM,)


def test_evaluation_is_deterministic_and_does_not_mutate_input() -> None:
    inputs = eligible_inputs()
    snapshot = deepcopy(inputs)
    evaluator = RemunerationEligibilityEvaluator()

    direct = evaluator.evaluate(inputs)
    reversed_result = evaluator.evaluate(tuple(reversed(inputs)))

    assert direct == reversed_result
    assert inputs == snapshot


def test_result_is_immutable_and_uses_no_loose_metadata() -> None:
    result = evaluate(eligible_inputs())

    assert not hasattr(result, "metadata")
    with pytest.raises(AttributeError):
        result.status = RemunerationEligibilityStatus.NOT_ELIGIBLE  # type: ignore[misc]
