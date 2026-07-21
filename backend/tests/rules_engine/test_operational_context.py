from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

import pytest

from supervisor_ai.rules_engine import (
    CandidateDomainEvent,
    CommercialAuthorRule,
    ConclusionKind,
    ConclusionStatus,
    DuplicateAuthorRule,
    EvaluationConclusion,
    EvaluationContext,
    Justification,
    ManualReviewRule,
    OperationalContextEligibilityRule,
    OperationalDecisionName,
    OperationalFactName,
    Rule,
    RulePhase,
    TicketPresenceRule,
    TicketSupportRule,
)

OBSERVED_AT = datetime(2026, 7, 20, tzinfo=UTC)
EVALUATION_ID = UUID("12345678-1234-5678-1234-567812345678")


def make_context() -> EvaluationContext:
    return EvaluationContext(
        evaluation_id=EVALUATION_ID,
        subject_id="commercial-event:456",
        observed_at=OBSERVED_AT,
        evidence=(),
    )


def conclusion(
    name: str,
    *,
    status: ConclusionStatus = ConclusionStatus.TRUE,
    value: str | tuple[str, ...] | None = None,
    suffix: str = "1",
) -> EvaluationConclusion:
    return EvaluationConclusion(
        conclusion_id=f"input.{name}.{suffix}",
        name=name,
        kind=ConclusionKind.DERIVED_FACT,
        status=status,
        justification=Justification(rule_id="input", summary="Prepared fact."),
        value=value,
    )


@pytest.mark.parametrize(
    ("rule", "fact_name", "expected_name"),
    [
        (
            TicketPresenceRule(),
            OperationalFactName.TICKET_FOUND,
            OperationalDecisionName.TICKET_PRESENT,
        ),
        (
            TicketPresenceRule(),
            OperationalFactName.TICKET_NOT_FOUND,
            OperationalDecisionName.TICKET_MISSING,
        ),
        (
            TicketSupportRule(),
            OperationalFactName.TICKET_OPENED_BY_SUPPORT,
            OperationalDecisionName.SUPPORT_TICKET,
        ),
        (
            TicketSupportRule(),
            OperationalFactName.TICKET_OPENED_OUTSIDE_SUPPORT,
            OperationalDecisionName.NON_SUPPORT_TICKET,
        ),
        (
            CommercialAuthorRule(),
            OperationalFactName.TICKET_AUTHOR_IDENTIFIED,
            OperationalDecisionName.COMMERCIAL_AUTHOR_IDENTIFIED,
        ),
        (
            CommercialAuthorRule(),
            OperationalFactName.TICKET_AUTHOR_MISSING,
            OperationalDecisionName.COMMERCIAL_AUTHOR_MISSING,
        ),
        (
            DuplicateAuthorRule(),
            OperationalFactName.DUPLICATE_AUTHOR_DETECTED,
            OperationalDecisionName.DUPLICATE_AUTHOR,
        ),
        (
            DuplicateAuthorRule(),
            OperationalFactName.DUPLICATE_AUTHOR_NOT_DETECTED,
            OperationalDecisionName.NO_DUPLICATE_AUTHOR,
        ),
    ],
)
def test_direct_operational_classifications(
    rule: Rule, fact_name: str, expected_name: str
) -> None:
    source = conclusion(fact_name, value="operator:42")

    result = rule.evaluate(make_context(), (source,))

    assert len(result) == 1
    assert result[0].name == expected_name
    assert result[0].status is ConclusionStatus.TRUE
    assert result[0].kind is ConclusionKind.DOMAIN_DECISION
    assert result[0].value == "operator:42"
    assert result[0].justification.supporting_conclusion_ids == (source.conclusion_id,)


@pytest.mark.parametrize(
    ("rule", "source_name", "status", "expected_name"),
    [
        (
            TicketPresenceRule(),
            OperationalFactName.TICKET_LOOKUP_NOT_EVALUABLE,
            ConclusionStatus.NOT_EVALUABLE,
            OperationalDecisionName.TICKET_PRESENCE_NOT_EVALUABLE,
        ),
        (
            TicketPresenceRule(),
            OperationalFactName.TICKET_LOOKUP_INCONSISTENT,
            ConclusionStatus.INCONSISTENT,
            OperationalDecisionName.TICKET_PRESENCE_INCONSISTENT,
        ),
        (
            TicketSupportRule(),
            OperationalFactName.TICKET_AREA_NOT_EVALUABLE,
            ConclusionStatus.NOT_EVALUABLE,
            OperationalDecisionName.TICKET_SUPPORT_NOT_EVALUABLE,
        ),
        (
            CommercialAuthorRule(),
            OperationalFactName.TICKET_AUTHORSHIP_INCONSISTENT,
            ConclusionStatus.INCONSISTENT,
            OperationalDecisionName.COMMERCIAL_AUTHOR_INCONSISTENT,
        ),
        (
            DuplicateAuthorRule(),
            OperationalFactName.DUPLICATE_AUTHOR_NOT_EVALUABLE,
            ConclusionStatus.NOT_EVALUABLE,
            OperationalDecisionName.DUPLICATE_AUTHOR_NOT_EVALUABLE,
        ),
    ],
)
def test_absence_and_inconsistency_are_explicit(
    rule: Rule, source_name: str, status: ConclusionStatus, expected_name: str
) -> None:
    result = rule.evaluate(make_context(), (conclusion(source_name, status=status),))

    assert [(item.name, item.status) for item in result] == [(expected_name, status)]


def operationally_eligible_inputs() -> tuple[EvaluationConclusion, ...]:
    return (
        conclusion(OperationalDecisionName.TICKET_PRESENT),
        conclusion(OperationalDecisionName.SUPPORT_TICKET),
        conclusion(
            OperationalDecisionName.COMMERCIAL_AUTHOR_IDENTIFIED,
            value="ticket-author:42",
        ),
        conclusion(OperationalDecisionName.NO_DUPLICATE_AUTHOR),
    )


def test_operational_context_is_eligible_when_all_requirements_are_met() -> None:
    result = OperationalContextEligibilityRule().evaluate(
        make_context(), operationally_eligible_inputs()
    )

    assert result[0].name is OperationalDecisionName.OPERATIONAL_CONTEXT_ELIGIBLE
    assert result[0].status is ConclusionStatus.TRUE


@pytest.mark.parametrize(
    ("index", "replacement"),
    [
        (0, OperationalDecisionName.TICKET_MISSING),
        (1, OperationalDecisionName.NON_SUPPORT_TICKET),
        (2, OperationalDecisionName.COMMERCIAL_AUTHOR_MISSING),
    ],
)
def test_operational_context_is_ineligible(
    index: int, replacement: OperationalDecisionName
) -> None:
    inputs = list(operationally_eligible_inputs())
    inputs[index] = conclusion(replacement)

    result = OperationalContextEligibilityRule().evaluate(make_context(), tuple(inputs))

    assert result[0].name is OperationalDecisionName.OPERATIONAL_CONTEXT_INELIGIBLE
    assert result[0].status is ConclusionStatus.TRUE


def test_duplicate_author_requires_review_and_is_not_evaluable() -> None:
    inputs = list(operationally_eligible_inputs())
    inputs[3] = conclusion(
        OperationalDecisionName.DUPLICATE_AUTHOR,
        value=("ticket-author:42", "ticket-author:84"),
    )

    eligibility = OperationalContextEligibilityRule().evaluate(
        make_context(), tuple(inputs)
    )
    review = ManualReviewRule().evaluate(make_context(), tuple(inputs))

    assert eligibility[0].name is (
        OperationalDecisionName.OPERATIONAL_CONTEXT_NOT_EVALUABLE
    )
    assert eligibility[0].status is ConclusionStatus.NOT_EVALUABLE
    assert review[0].name is OperationalDecisionName.MANUAL_REVIEW_REQUIRED


def test_executor_different_from_ticket_author_does_not_change_eligibility() -> None:
    inputs = (
        *operationally_eligible_inputs(),
        conclusion(OperationalFactName.EXECUTOR_IDENTIFIED, value="executor:99"),
    )

    result = OperationalContextEligibilityRule().evaluate(make_context(), inputs)

    assert result[0].name is OperationalDecisionName.OPERATIONAL_CONTEXT_ELIGIBLE
    assert all(
        "executor" not in identifier
        for identifier in result[0].justification.supporting_conclusion_ids
    )


def test_commercial_author_is_derived_only_from_ticket_author() -> None:
    ticket_author = conclusion(
        OperationalFactName.TICKET_AUTHOR_IDENTIFIED,
        value="ticket-author:42",
    )
    executor = conclusion(
        OperationalFactName.EXECUTOR_IDENTIFIED,
        value="executor:99",
    )

    result = CommercialAuthorRule().evaluate(
        make_context(), (executor, ticket_author)
    )

    assert result[0].value == "ticket-author:42"
    assert result[0].justification.supporting_conclusion_ids == (
        ticket_author.conclusion_id,
    )


def test_missing_executor_does_not_change_eligibility() -> None:
    with_executor_missing = (
        *operationally_eligible_inputs(),
        conclusion(OperationalFactName.EXECUTOR_MISSING),
    )
    rule = OperationalContextEligibilityRule()

    without_executor = rule.evaluate(make_context(), operationally_eligible_inputs())
    explicit_missing = rule.evaluate(make_context(), with_executor_missing)

    assert without_executor == explicit_missing


def test_required_input_not_evaluable_propagates() -> None:
    inputs = list(operationally_eligible_inputs())
    inputs[1] = conclusion(
        OperationalDecisionName.TICKET_SUPPORT_NOT_EVALUABLE,
        status=ConclusionStatus.NOT_EVALUABLE,
    )

    result = OperationalContextEligibilityRule().evaluate(make_context(), tuple(inputs))

    assert result[0].name is (OperationalDecisionName.OPERATIONAL_CONTEXT_NOT_EVALUABLE)
    assert result[0].status is ConclusionStatus.NOT_EVALUABLE


def test_inconsistent_input_has_precedence() -> None:
    inputs = list(operationally_eligible_inputs())
    inputs[1] = conclusion(
        OperationalDecisionName.TICKET_SUPPORT_INCONSISTENT,
        status=ConclusionStatus.INCONSISTENT,
    )

    result = OperationalContextEligibilityRule().evaluate(make_context(), tuple(inputs))

    assert result[0].name is (OperationalDecisionName.OPERATIONAL_CONTEXT_INCONSISTENT)
    assert result[0].status is ConclusionStatus.INCONSISTENT


def test_duplicate_conclusion_name_is_inconsistent() -> None:
    inputs = (
        *operationally_eligible_inputs(),
        conclusion(OperationalDecisionName.TICKET_PRESENT, suffix="2"),
    )

    result = OperationalContextEligibilityRule().evaluate(make_context(), inputs)

    assert result[0].name is (OperationalDecisionName.OPERATIONAL_CONTEXT_INCONSISTENT)


def test_manual_review_is_not_requested_without_duplicate_author() -> None:
    clear = conclusion(OperationalDecisionName.NO_DUPLICATE_AUTHOR)

    result = ManualReviewRule().evaluate(make_context(), (clear,))

    assert result == ()


def test_rules_are_structural_deterministic_and_do_not_mutate_inputs() -> None:
    rules = (
        TicketPresenceRule(),
        TicketSupportRule(),
        CommercialAuthorRule(),
        DuplicateAuthorRule(),
        ManualReviewRule(),
        OperationalContextEligibilityRule(),
    )
    context = make_context()
    available = operationally_eligible_inputs()
    original_context = deepcopy(context)
    original_available = deepcopy(available)

    for rule in rules:
        assert isinstance(rule, Rule)
        assert rule.phase is RulePhase.AUTHORSHIP_AND_ELIGIBILITY
        assert rule.evaluate(context, available) == rule.evaluate(
            context, tuple(reversed(available))
        )

    assert context == original_context
    assert available == original_available


def test_phase_c_has_no_commercial_classification_dependency() -> None:
    source = __import__(
        "supervisor_ai.rules_engine.operational_context", fromlist=["unused"]
    )

    assert "CommercialClassificationName" not in vars(source)


def test_no_rule_produces_candidate_domain_events() -> None:
    result = OperationalContextEligibilityRule().evaluate(
        make_context(), operationally_eligible_inputs()
    )

    assert all(not isinstance(item, CandidateDomainEvent) for item in result)
