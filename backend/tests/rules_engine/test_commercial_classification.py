from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from supervisor_ai.rules_engine import (
    CandidateDomainEvent,
    CommercialClassificationName,
    CommonAdditionalClassificationRule,
    CommonAdditionalsComparisonRule,
    ConclusionKind,
    ConclusionStatus,
    ContractualEvidenceName,
    ContractualFactName,
    EvaluationConclusion,
    EvaluationContext,
    Evidence,
    EvidenceValue,
    Justification,
    MeshComparisonRule,
    OperationScopeClassificationRule,
    PlanChangeClassificationRule,
    PlanModalityComparisonRule,
    RecurringRevenueClassificationRule,
    RecurringValueComparisonRule,
    Rule,
    RulePhase,
    SpeedComparisonRule,
)

OBSERVED_AT = datetime(2026, 7, 20, tzinfo=UTC)
EVALUATION_ID = UUID("12345678-1234-5678-1234-567812345678")


def make_context(*evidence: Evidence) -> EvaluationContext:
    return EvaluationContext(
        evaluation_id=EVALUATION_ID,
        subject_id="commercial-event:456",
        observed_at=OBSERVED_AT,
        evidence=evidence,
    )


def make_evidence(
    name: ContractualEvidenceName,
    value: EvidenceValue,
) -> Evidence:
    return Evidence(
        evidence_id=f"evidence.{name}",
        name=name,
        value=value,
        observed_at=OBSERVED_AT,
    )


def make_conclusion(
    name: str,
    *,
    status: ConclusionStatus = ConclusionStatus.TRUE,
    value: EvidenceValue = None,
    suffix: str = "1",
) -> EvaluationConclusion:
    return EvaluationConclusion(
        conclusion_id=f"phase-a.{name}.{suffix}",
        name=name,
        kind=ConclusionKind.DERIVED_FACT,
        status=status,
        justification=Justification(rule_id="phase-a", summary="Phase A fact."),
        value=value,
    )


def unchanged_plan_facts() -> tuple[EvaluationConclusion, ...]:
    return (
        make_conclusion(ContractualFactName.SPEED_UNCHANGED),
        make_conclusion(ContractualFactName.PLAN_MODALITY_UNCHANGED),
        make_conclusion(ContractualFactName.MESH_UNCHANGED),
    )


@pytest.mark.parametrize(
    "changed_fact",
    [
        ContractualFactName.SPEED_INCREASED,
        ContractualFactName.SPEED_DECREASED,
        ContractualFactName.PLAN_MODALITY_CHANGED,
        ContractualFactName.MESH_INCLUDED,
        ContractualFactName.MESH_REMOVED,
    ],
)
def test_plan_change_is_classified_from_each_supported_fact(
    changed_fact: ContractualFactName,
) -> None:
    facts = list(unchanged_plan_facts())
    if changed_fact in {
        ContractualFactName.SPEED_INCREASED,
        ContractualFactName.SPEED_DECREASED,
    }:
        facts[0] = make_conclusion(changed_fact)
    elif changed_fact is ContractualFactName.PLAN_MODALITY_CHANGED:
        facts[1] = make_conclusion(changed_fact)
    else:
        facts[2] = make_conclusion(changed_fact)

    result = PlanChangeClassificationRule().evaluate(make_context(), tuple(facts))

    assert [(item.name, item.status) for item in result] == [
        (CommercialClassificationName.PLAN_CHANGED, ConclusionStatus.TRUE)
    ]


def test_common_additional_alone_does_not_change_plan() -> None:
    plan_facts = unchanged_plan_facts()
    facts = plan_facts + (
        make_conclusion(ContractualFactName.COMMON_ADDITIONAL_INCLUDED),
    )

    result = PlanChangeClassificationRule().evaluate(make_context(), facts)

    assert result[0].name == CommercialClassificationName.PLAN_UNCHANGED
    assert result[0].justification.supporting_conclusion_ids == tuple(
        sorted(item.conclusion_id for item in plan_facts)
    )


def test_all_unchanged_plan_components_produce_plan_unchanged() -> None:
    result = PlanChangeClassificationRule().evaluate(
        make_context(), unchanged_plan_facts()
    )

    assert result[0].name == CommercialClassificationName.PLAN_UNCHANGED


def test_plan_change_is_not_evaluable_when_a_required_fact_is_missing() -> None:
    facts = unchanged_plan_facts()[:2]

    result = PlanChangeClassificationRule().evaluate(make_context(), facts)

    assert [(item.name, item.status) for item in result] == [
        (
            CommercialClassificationName.PLAN_CHANGE_NOT_EVALUABLE,
            ConclusionStatus.NOT_EVALUABLE,
        )
    ]


def test_plan_change_propagates_inconsistency_before_absence() -> None:
    facts = (
        make_conclusion(
            ContractualFactName.SPEED_INCONSISTENT,
            status=ConclusionStatus.INCONSISTENT,
        ),
        make_conclusion(
            ContractualFactName.PLAN_MODALITY_NOT_EVALUABLE,
            status=ConclusionStatus.NOT_EVALUABLE,
        ),
    )

    result = PlanChangeClassificationRule().evaluate(make_context(), facts)

    assert [(item.name, item.status) for item in result] == [
        (
            CommercialClassificationName.PLAN_CHANGE_INCONSISTENT,
            ConclusionStatus.INCONSISTENT,
        )
    ]


def test_plan_change_is_independent_of_conclusion_order() -> None:
    facts = (
        make_conclusion(ContractualFactName.SPEED_INCREASED),
        make_conclusion(ContractualFactName.PLAN_MODALITY_UNCHANGED),
        make_conclusion(ContractualFactName.MESH_UNCHANGED),
    )
    rule = PlanChangeClassificationRule()

    assert rule.evaluate(make_context(), facts) == rule.evaluate(
        make_context(), tuple(reversed(facts))
    )


def test_duplicate_fact_name_makes_plan_change_inconsistent() -> None:
    facts = unchanged_plan_facts() + (
        make_conclusion(ContractualFactName.SPEED_UNCHANGED, suffix="2"),
    )

    result = PlanChangeClassificationRule().evaluate(make_context(), facts)

    assert result[0].name == CommercialClassificationName.PLAN_CHANGE_INCONSISTENT
    assert result[0].status is ConclusionStatus.INCONSISTENT


@pytest.mark.parametrize(
    ("source_name", "expected_name"),
    [
        (
            ContractualFactName.RECURRING_VALUE_INCREASED,
            CommercialClassificationName.COMMERCIAL_UPGRADE,
        ),
        (
            ContractualFactName.RECURRING_VALUE_DECREASED,
            CommercialClassificationName.COMMERCIAL_DOWNGRADE,
        ),
        (
            ContractualFactName.RECURRING_VALUE_UNCHANGED,
            CommercialClassificationName.RECURRING_REVENUE_UNCHANGED,
        ),
    ],
)
def test_recurring_revenue_classification(
    source_name: ContractualFactName,
    expected_name: CommercialClassificationName,
) -> None:
    source = make_conclusion(
        source_name,
        value=(Decimal("89.90"), Decimal("99.90")),
    )

    result = RecurringRevenueClassificationRule().evaluate(
        make_context(), (source,)
    )

    assert [(item.name, item.status) for item in result] == [
        (expected_name, ConclusionStatus.TRUE)
    ]
    assert result[0].justification.supporting_conclusion_ids == (
        source.conclusion_id,
    )


def test_financial_classification_never_emits_upgrade_and_downgrade_together() -> None:
    facts = (
        make_conclusion(ContractualFactName.RECURRING_VALUE_INCREASED),
        make_conclusion(ContractualFactName.RECURRING_VALUE_DECREASED),
    )

    result = RecurringRevenueClassificationRule().evaluate(make_context(), facts)

    assert result[0].name == (
        CommercialClassificationName.RECURRING_REVENUE_INCONSISTENT
    )
    assert result[0].status is ConclusionStatus.INCONSISTENT


@pytest.mark.parametrize(
    ("source_name", "source_status", "expected_name", "expected_status"),
    [
        (
            ContractualFactName.RECURRING_VALUE_NOT_EVALUABLE,
            ConclusionStatus.NOT_EVALUABLE,
            CommercialClassificationName.RECURRING_REVENUE_NOT_EVALUABLE,
            ConclusionStatus.NOT_EVALUABLE,
        ),
        (
            ContractualFactName.RECURRING_VALUE_INCONSISTENT,
            ConclusionStatus.INCONSISTENT,
            CommercialClassificationName.RECURRING_REVENUE_INCONSISTENT,
            ConclusionStatus.INCONSISTENT,
        ),
    ],
)
def test_financial_classification_preserves_unresolved_state(
    source_name: ContractualFactName,
    source_status: ConclusionStatus,
    expected_name: CommercialClassificationName,
    expected_status: ConclusionStatus,
) -> None:
    result = RecurringRevenueClassificationRule().evaluate(
        make_context(),
        (make_conclusion(source_name, status=source_status),),
    )

    assert [(item.name, item.status) for item in result] == [
        (expected_name, expected_status)
    ]


def test_financial_classification_is_not_evaluable_without_revenue_fact() -> None:
    result = RecurringRevenueClassificationRule().evaluate(make_context(), ())

    assert result[0].name == (
        CommercialClassificationName.RECURRING_REVENUE_NOT_EVALUABLE
    )


@pytest.mark.parametrize(
    ("revenue_fact", "expected"),
    [
        (
            ContractualFactName.RECURRING_VALUE_INCREASED,
            CommercialClassificationName.COMMERCIAL_UPGRADE,
        ),
        (
            ContractualFactName.RECURRING_VALUE_DECREASED,
            CommercialClassificationName.COMMERCIAL_DOWNGRADE,
        ),
        (
            ContractualFactName.RECURRING_VALUE_UNCHANGED,
            CommercialClassificationName.RECURRING_REVENUE_UNCHANGED,
        ),
    ],
)
def test_modality_change_does_not_determine_financial_direction(
    revenue_fact: ContractualFactName,
    expected: CommercialClassificationName,
) -> None:
    facts = (
        make_conclusion(ContractualFactName.PLAN_MODALITY_CHANGED),
        make_conclusion(revenue_fact),
    )

    result = RecurringRevenueClassificationRule().evaluate(make_context(), facts)

    assert result[0].name == expected


@pytest.mark.parametrize(
    ("facts", "expected_names"),
    [
        (
            (
                make_conclusion(
                    ContractualFactName.COMMON_ADDITIONAL_INCLUDED,
                    value=("Public IP",),
                ),
            ),
            (CommercialClassificationName.COMMON_ADDITIONAL_SALE,),
        ),
        (
            (
                make_conclusion(
                    ContractualFactName.COMMON_ADDITIONAL_REMOVED,
                    value=("Watch TV",),
                ),
            ),
            (CommercialClassificationName.COMMON_ADDITIONAL_REMOVAL,),
        ),
        (
            (
                make_conclusion(
                    ContractualFactName.COMMON_ADDITIONAL_INCLUDED,
                    value=("Public IP",),
                ),
                make_conclusion(
                    ContractualFactName.COMMON_ADDITIONAL_REMOVED,
                    value=("Watch TV",),
                ),
            ),
            (
                CommercialClassificationName.COMMON_ADDITIONAL_SALE,
                CommercialClassificationName.COMMON_ADDITIONAL_REMOVAL,
            ),
        ),
    ],
)
def test_common_additional_classification_preserves_changes_and_values(
    facts: tuple[EvaluationConclusion, ...],
    expected_names: tuple[CommercialClassificationName, ...],
) -> None:
    result = CommonAdditionalClassificationRule().evaluate(make_context(), facts)

    assert tuple(item.name for item in result) == expected_names
    assert tuple(item.value for item in result) == tuple(item.value for item in facts)


def test_additional_only_operation() -> None:
    plan = make_conclusion(CommercialClassificationName.PLAN_UNCHANGED)
    additional = make_conclusion(ContractualFactName.COMMON_ADDITIONAL_INCLUDED)

    result = OperationScopeClassificationRule().evaluate(
        make_context(), (plan, additional)
    )

    assert result[0].name == CommercialClassificationName.ADDITIONAL_ONLY_OPERATION


def test_simultaneous_additional_changes_remain_additional_only() -> None:
    facts = (
        make_conclusion(CommercialClassificationName.PLAN_UNCHANGED),
        make_conclusion(ContractualFactName.COMMON_ADDITIONAL_INCLUDED),
        make_conclusion(ContractualFactName.COMMON_ADDITIONAL_REMOVED),
    )

    result = OperationScopeClassificationRule().evaluate(make_context(), facts)

    assert [item.name for item in result] == [
        CommercialClassificationName.ADDITIONAL_ONLY_OPERATION
    ]


def test_mixed_plan_and_additional_operation_replaces_additional_only() -> None:
    plan = make_conclusion(CommercialClassificationName.PLAN_CHANGED)
    additional = make_conclusion(ContractualFactName.COMMON_ADDITIONAL_INCLUDED)

    result = OperationScopeClassificationRule().evaluate(
        make_context(), (additional, plan)
    )

    assert [item.name for item in result] == [
        CommercialClassificationName.MIXED_PLAN_AND_ADDITIONAL_OPERATION
    ]


def test_mesh_is_not_classified_as_common_additional() -> None:
    facts = (
        make_conclusion(ContractualFactName.MESH_INCLUDED),
        make_conclusion(ContractualFactName.COMMON_ADDITIONALS_UNCHANGED),
    )

    result = CommonAdditionalClassificationRule().evaluate(make_context(), facts)

    assert result == ()


def test_duplicate_additional_fact_is_inconsistent() -> None:
    facts = (
        make_conclusion(ContractualFactName.COMMON_ADDITIONAL_INCLUDED, suffix="1"),
        make_conclusion(ContractualFactName.COMMON_ADDITIONAL_INCLUDED, suffix="2"),
    )

    result = CommonAdditionalClassificationRule().evaluate(make_context(), facts)

    assert result[0].name == (
        CommercialClassificationName.COMMON_ADDITIONAL_CLASSIFICATION_INCONSISTENT
    )
    assert result[0].status is ConclusionStatus.INCONSISTENT


def run_phase_a(context: EvaluationContext) -> tuple[EvaluationConclusion, ...]:
    conclusions: list[EvaluationConclusion] = []
    for rule in (
        SpeedComparisonRule(),
        PlanModalityComparisonRule(),
        MeshComparisonRule(),
        CommonAdditionalsComparisonRule(),
        RecurringValueComparisonRule(),
    ):
        conclusions.extend(rule.evaluate(context, ()))
    return tuple(conclusions)


def run_phase_b(
    context: EvaluationContext,
    phase_a: tuple[EvaluationConclusion, ...],
) -> tuple[EvaluationConclusion, ...]:
    conclusions: list[EvaluationConclusion] = []
    for rule in (
        PlanChangeClassificationRule(),
        RecurringRevenueClassificationRule(),
        CommonAdditionalClassificationRule(),
    ):
        conclusions.extend(rule.evaluate(context, phase_a))
    conclusions.extend(
        OperationScopeClassificationRule().evaluate(
            context, phase_a + tuple(conclusions)
        )
    )
    return tuple(conclusions)


def scenario_context(
    *,
    previous_speed: int,
    current_speed: int,
    previous_modality: str = "standard",
    current_modality: str = "standard",
    previous_mesh: bool = False,
    current_mesh: bool = False,
    previous_additionals: tuple[str, ...] = (),
    current_additionals: tuple[str, ...] = (),
    previous_value: Decimal,
    current_value: Decimal,
) -> EvaluationContext:
    return make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, previous_speed),
        make_evidence(ContractualEvidenceName.CURRENT_SPEED, current_speed),
        make_evidence(
            ContractualEvidenceName.PREVIOUS_PLAN_MODALITY, previous_modality
        ),
        make_evidence(
            ContractualEvidenceName.CURRENT_PLAN_MODALITY, current_modality
        ),
        make_evidence(
            ContractualEvidenceName.PREVIOUS_MESH_ENABLED, previous_mesh
        ),
        make_evidence(ContractualEvidenceName.CURRENT_MESH_ENABLED, current_mesh),
        make_evidence(
            ContractualEvidenceName.PREVIOUS_ADDITIONALS, previous_additionals
        ),
        make_evidence(
            ContractualEvidenceName.CURRENT_ADDITIONALS, current_additionals
        ),
        make_evidence(
            ContractualEvidenceName.PREVIOUS_RECURRING_VALUE, previous_value
        ),
        make_evidence(
            ContractualEvidenceName.CURRENT_RECURRING_VALUE, current_value
        ),
    )


@pytest.mark.parametrize(
    ("context", "expected", "unexpected"),
    [
        (
            scenario_context(
                previous_speed=500,
                current_speed=1000,
                previous_value=Decimal("89.90"),
                current_value=Decimal("99.90"),
            ),
            {"plan_changed", "commercial_upgrade"},
            {"common_additional_sale", "additional_only_operation"},
        ),
        (
            scenario_context(
                previous_speed=1000,
                current_speed=1000,
                current_additionals=("Public IP",),
                previous_value=Decimal("99.90"),
                current_value=Decimal("119.90"),
            ),
            {
                "plan_unchanged",
                "commercial_upgrade",
                "common_additional_sale",
                "additional_only_operation",
            },
            {"mixed_plan_and_additional_operation"},
        ),
        (
            scenario_context(
                previous_speed=1000,
                current_speed=1000,
                current_mesh=True,
                previous_value=Decimal("99.90"),
                current_value=Decimal("119.90"),
            ),
            {"plan_changed", "commercial_upgrade"},
            {"common_additional_sale", "additional_only_operation"},
        ),
        (
            scenario_context(
                previous_speed=1500,
                current_speed=1000,
                current_additionals=("Public IP",),
                previous_value=Decimal("119.90"),
                current_value=Decimal("109.90"),
            ),
            {
                "plan_changed",
                "commercial_downgrade",
                "common_additional_sale",
                "mixed_plan_and_additional_operation",
            },
            {"additional_only_operation"},
        ),
        (
            scenario_context(
                previous_speed=1000,
                current_speed=1000,
                previous_modality="standard",
                current_modality="promotional",
                previous_value=Decimal("99.90"),
                current_value=Decimal("89.90"),
            ),
            {"plan_changed", "commercial_downgrade"},
            {"commercial_upgrade", "recurring_revenue_unchanged"},
        ),
        (
            scenario_context(
                previous_speed=1000,
                current_speed=1000,
                previous_additionals=("Public IP",),
                previous_value=Decimal("119.90"),
                current_value=Decimal("99.90"),
            ),
            {
                "plan_unchanged",
                "commercial_downgrade",
                "common_additional_removal",
                "additional_only_operation",
            },
            {"mixed_plan_and_additional_operation"},
        ),
    ],
)
def test_integrated_commercial_scenarios(
    context: EvaluationContext,
    expected: set[str],
    unexpected: set[str],
) -> None:
    phase_a = run_phase_a(context)
    names = {item.name for item in run_phase_b(context, phase_a)}

    assert expected <= names
    assert not unexpected & names


def test_rules_are_structural_phase_b_rules_without_side_effects() -> None:
    rules = (
        PlanChangeClassificationRule(),
        RecurringRevenueClassificationRule(),
        CommonAdditionalClassificationRule(),
        OperationScopeClassificationRule(),
    )
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, 1)
    )
    context_snapshot = deepcopy(context)
    available = unchanged_plan_facts() + (
        make_conclusion(ContractualFactName.COMMON_ADDITIONALS_UNCHANGED),
        make_conclusion(ContractualFactName.RECURRING_VALUE_UNCHANGED),
    )
    available_snapshot = deepcopy(available)

    first = tuple(rule.evaluate(context, available) for rule in rules)
    second = tuple(rule.evaluate(context, available) for rule in rules)

    assert all(isinstance(rule, Rule) for rule in rules)
    assert all(rule.phase is RulePhase.COMMERCIAL_CLASSIFICATION for rule in rules)
    assert context == context_snapshot
    assert available == available_snapshot
    assert first == second
    assert all(
        conclusion.kind is ConclusionKind.DOMAIN_DECISION
        for result in first
        for conclusion in result
    )
    assert not any(
        isinstance(conclusion, CandidateDomainEvent)
        for result in first
        for conclusion in result
    )


def test_phase_b_results_depend_only_on_available_conclusions() -> None:
    facts = unchanged_plan_facts()
    empty_context = make_context()
    unrelated_context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, 1),
        make_evidence(ContractualEvidenceName.CURRENT_SPEED, 9999),
    )
    rule = PlanChangeClassificationRule()

    assert rule.evaluate(empty_context, facts) == rule.evaluate(
        unrelated_context, facts
    )


def test_justification_references_every_used_conclusion() -> None:
    facts = unchanged_plan_facts()

    result = PlanChangeClassificationRule().evaluate(make_context(), facts)

    assert result[0].justification.supporting_conclusion_ids == tuple(
        sorted(item.conclusion_id for item in facts)
    )
