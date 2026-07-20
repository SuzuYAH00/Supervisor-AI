from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from supervisor_ai.rules_engine import (
    CandidateDomainEvent,
    CommonAdditionalsComparisonRule,
    ConclusionKind,
    ConclusionStatus,
    ContractualEvidenceName,
    EvaluationConclusion,
    EvaluationContext,
    Evidence,
    EvidenceValue,
    MeshComparisonRule,
    PlanModalityComparisonRule,
    RecurringValueComparisonRule,
    Rule,
    RulePhase,
    SpeedComparisonRule,
)

OBSERVED_AT = datetime(2026, 7, 20, tzinfo=UTC)
EVALUATION_ID = UUID("12345678-1234-5678-1234-567812345678")


def make_evidence(
    name: ContractualEvidenceName,
    value: EvidenceValue,
    *,
    suffix: str = "1",
) -> Evidence:
    return Evidence(
        evidence_id=f"{name}.{suffix}",
        name=name,
        value=value,
        observed_at=OBSERVED_AT,
        source_reference="contract:123",
    )


def make_context(*evidence: Evidence) -> EvaluationContext:
    return EvaluationContext(
        evaluation_id=EVALUATION_ID,
        subject_id="commercial-event:456",
        observed_at=OBSERVED_AT,
        evidence=evidence,
    )


def conclusions_by_name(
    conclusions: tuple[EvaluationConclusion, ...],
) -> dict[str, EvaluationConclusion]:
    return {conclusion.name: conclusion for conclusion in conclusions}


@pytest.mark.parametrize(
    ("previous", "current", "expected_true"),
    [
        (500, 1000, "speed_increased"),
        (1000, 500, "speed_decreased"),
        (1000, 1000, "speed_unchanged"),
    ],
)
def test_speed_comparison(
    previous: int,
    current: int,
    expected_true: str,
) -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, previous),
        make_evidence(ContractualEvidenceName.CURRENT_SPEED, current),
    )

    conclusions = SpeedComparisonRule().evaluate(context, ())

    assert len(conclusions) == 1
    assert conclusions[0].name == expected_true
    assert conclusions[0].status is ConclusionStatus.TRUE
    assert conclusions[0].value == (previous, current)


def test_speed_is_not_evaluable_when_evidence_is_missing() -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, 500)
    )

    conclusions = SpeedComparisonRule().evaluate(context, ())

    assert [(item.name, item.status) for item in conclusions] == [
        ("speed_not_evaluable", ConclusionStatus.NOT_EVALUABLE)
    ]


@pytest.mark.parametrize("invalid_value", [True, "1000", 1000.0])
def test_speed_is_inconsistent_for_invalid_type(
    invalid_value: EvidenceValue,
) -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, 500),
        make_evidence(ContractualEvidenceName.CURRENT_SPEED, invalid_value),
    )

    assert [
        (item.name, item.status)
        for item in SpeedComparisonRule().evaluate(context, ())
    ] == [("speed_inconsistent", ConclusionStatus.INCONSISTENT)]


def test_speed_is_inconsistent_for_conflicting_evidence() -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, 500),
        make_evidence(ContractualEvidenceName.CURRENT_SPEED, 1000, suffix="1"),
        make_evidence(ContractualEvidenceName.CURRENT_SPEED, 1500, suffix="2"),
    )

    assert [
        (item.name, item.status)
        for item in SpeedComparisonRule().evaluate(context, ())
    ] == [("speed_inconsistent", ConclusionStatus.INCONSISTENT)]


@pytest.mark.parametrize(
    ("previous", "current", "expected_true"),
    [
        ("standard", "promotional", "plan_modality_changed"),
        ("standard", "standard", "plan_modality_unchanged"),
    ],
)
def test_plan_modality_comparison(
    previous: str,
    current: str,
    expected_true: str,
) -> None:
    context = make_context(
        make_evidence(
            ContractualEvidenceName.PREVIOUS_PLAN_MODALITY, previous
        ),
        make_evidence(ContractualEvidenceName.CURRENT_PLAN_MODALITY, current),
    )

    conclusions = PlanModalityComparisonRule().evaluate(context, ())

    assert [(item.name, item.status) for item in conclusions] == [
        (expected_true, ConclusionStatus.TRUE)
    ]


def test_plan_modality_is_not_evaluable_when_evidence_is_missing() -> None:
    conclusions = PlanModalityComparisonRule().evaluate(make_context(), ())

    assert [(item.name, item.status) for item in conclusions] == [
        ("plan_modality_not_evaluable", ConclusionStatus.NOT_EVALUABLE)
    ]


def test_plan_modality_is_inconsistent_for_conflicting_evidence() -> None:
    context = make_context(
        make_evidence(
            ContractualEvidenceName.PREVIOUS_PLAN_MODALITY, "standard"
        ),
        make_evidence(
            ContractualEvidenceName.CURRENT_PLAN_MODALITY,
            "standard",
            suffix="1",
        ),
        make_evidence(
            ContractualEvidenceName.CURRENT_PLAN_MODALITY,
            "promotional",
            suffix="2",
        ),
    )

    conclusions = PlanModalityComparisonRule().evaluate(context, ())

    assert [(item.name, item.status) for item in conclusions] == [
        ("plan_modality_inconsistent", ConclusionStatus.INCONSISTENT)
    ]


@pytest.mark.parametrize(
    ("previous", "current", "expected_true"),
    [
        (False, True, "mesh_included"),
        (True, False, "mesh_removed"),
        (True, True, "mesh_unchanged"),
    ],
)
def test_mesh_comparison(
    previous: bool,
    current: bool,
    expected_true: str,
) -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_MESH_ENABLED, previous),
        make_evidence(ContractualEvidenceName.CURRENT_MESH_ENABLED, current),
    )

    conclusions = MeshComparisonRule().evaluate(context, ())

    assert [(item.name, item.status) for item in conclusions] == [
        (expected_true, ConclusionStatus.TRUE)
    ]


def test_mesh_is_not_evaluable_when_evidence_is_missing() -> None:
    conclusions = MeshComparisonRule().evaluate(make_context(), ())

    assert [(item.name, item.status) for item in conclusions] == [
        ("mesh_not_evaluable", ConclusionStatus.NOT_EVALUABLE)
    ]


def test_mesh_is_inconsistent_for_invalid_type() -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_MESH_ENABLED, False),
        make_evidence(ContractualEvidenceName.CURRENT_MESH_ENABLED, 1),
    )

    assert [
        (item.name, item.status)
        for item in MeshComparisonRule().evaluate(context, ())
    ] == [("mesh_inconsistent", ConclusionStatus.INCONSISTENT)]


@pytest.mark.parametrize(
    ("previous", "current", "included", "removed", "unchanged"),
    [
        ((), ("Public IP",), ("Public IP",), (), False),
        (("Watch TV",), (), (), ("Watch TV",), False),
        (
            ("Watch TV",),
            ("Public IP",),
            ("Public IP",),
            ("Watch TV",),
            False,
        ),
        (("Public IP",), ("Public IP",), (), (), True),
        (
            ("Public IP", "Watch TV"),
            ("Watch TV", "Public IP"),
            (),
            (),
            True,
        ),
    ],
)
def test_common_additionals_comparison(
    previous: tuple[str, ...],
    current: tuple[str, ...],
    included: tuple[str, ...],
    removed: tuple[str, ...],
    unchanged: bool,
) -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_ADDITIONALS, previous),
        make_evidence(ContractualEvidenceName.CURRENT_ADDITIONALS, current),
    )

    conclusions = CommonAdditionalsComparisonRule().evaluate(context, ())
    by_name = conclusions_by_name(conclusions)

    expected_names = set()
    if included:
        expected_names.add("common_additional_included")
        assert by_name["common_additional_included"].value == included
    if removed:
        expected_names.add("common_additional_removed")
        assert by_name["common_additional_removed"].value == removed
    if unchanged:
        expected_names.add("common_additionals_unchanged")
    assert set(by_name) == expected_names
    assert all(item.status is ConclusionStatus.TRUE for item in conclusions)


def test_mesh_is_excluded_from_common_additionals() -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_ADDITIONALS, ()),
        make_evidence(
            ContractualEvidenceName.CURRENT_ADDITIONALS,
            ("Mesh",),
        ),
    )

    conclusions = CommonAdditionalsComparisonRule().evaluate(context, ())

    assert [(item.name, item.status) for item in conclusions] == [
        ("common_additionals_unchanged", ConclusionStatus.TRUE)
    ]


def test_common_additionals_are_not_evaluable_when_evidence_is_missing() -> None:
    conclusions = CommonAdditionalsComparisonRule().evaluate(make_context(), ())

    assert [(item.name, item.status) for item in conclusions] == [
        ("common_additionals_not_evaluable", ConclusionStatus.NOT_EVALUABLE)
    ]


@pytest.mark.parametrize(
    "invalid_value",
    [("Public IP", "Public IP"), ("Public IP", 1), "Public IP"],
)
def test_common_additionals_are_inconsistent_for_duplicates_or_invalid_type(
    invalid_value: EvidenceValue,
) -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_ADDITIONALS, ()),
        make_evidence(ContractualEvidenceName.CURRENT_ADDITIONALS, invalid_value),
    )

    conclusions = CommonAdditionalsComparisonRule().evaluate(context, ())

    assert [(item.name, item.status) for item in conclusions] == [
        ("common_additionals_inconsistent", ConclusionStatus.INCONSISTENT)
    ]


@pytest.mark.parametrize(
    ("previous", "current", "expected_true"),
    [
        (Decimal("89.90"), Decimal("99.90"), "recurring_value_increased"),
        (Decimal("99.90"), Decimal("89.90"), "recurring_value_decreased"),
        (Decimal("99.90"), Decimal("99.90"), "recurring_value_unchanged"),
    ],
)
def test_recurring_value_comparison_uses_decimal_without_float_conversion(
    previous: Decimal,
    current: Decimal,
    expected_true: str,
) -> None:
    context = make_context(
        make_evidence(
            ContractualEvidenceName.PREVIOUS_RECURRING_VALUE, previous
        ),
        make_evidence(ContractualEvidenceName.CURRENT_RECURRING_VALUE, current),
    )

    conclusions = RecurringValueComparisonRule().evaluate(context, ())

    assert len(conclusions) == 1
    assert conclusions[0].name == expected_true
    assert conclusions[0].status is ConclusionStatus.TRUE
    assert conclusions[0].value == (previous, current)
    assert all(
        isinstance(value, Decimal)
        for value in conclusions[0].value  # type: ignore[union-attr]
    )


def test_recurring_value_is_not_evaluable_when_evidence_is_missing() -> None:
    conclusions = RecurringValueComparisonRule().evaluate(make_context(), ())

    assert [(item.name, item.status) for item in conclusions] == [
        ("recurring_value_not_evaluable", ConclusionStatus.NOT_EVALUABLE)
    ]


@pytest.mark.parametrize("invalid_value", [99.90, 100, "99.90", True])
def test_recurring_value_is_inconsistent_for_non_decimal(
    invalid_value: EvidenceValue,
) -> None:
    context = make_context(
        make_evidence(
            ContractualEvidenceName.PREVIOUS_RECURRING_VALUE,
            Decimal("89.90"),
        ),
        make_evidence(
            ContractualEvidenceName.CURRENT_RECURRING_VALUE, invalid_value
        ),
    )

    conclusions = RecurringValueComparisonRule().evaluate(context, ())

    assert [(item.name, item.status) for item in conclusions] == [
        ("recurring_value_inconsistent", ConclusionStatus.INCONSISTENT)
    ]


def test_all_rules_are_structural_contractual_fact_rules() -> None:
    rules = (
        SpeedComparisonRule(),
        PlanModalityComparisonRule(),
        MeshComparisonRule(),
        CommonAdditionalsComparisonRule(),
        RecurringValueComparisonRule(),
    )

    assert all(isinstance(rule, Rule) for rule in rules)
    assert all(rule.phase is RulePhase.CONTRACTUAL_FACTS for rule in rules)


def test_rules_do_not_modify_context_and_are_deterministic() -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, 500),
        make_evidence(ContractualEvidenceName.CURRENT_SPEED, 1000),
    )
    snapshot = deepcopy(context)
    rule = SpeedComparisonRule()

    first_result = rule.evaluate(context, ())
    second_result = rule.evaluate(context, ())

    assert context == snapshot
    assert first_result == second_result


def test_justifications_reference_all_used_evidence() -> None:
    evidence = (
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, 500),
        make_evidence(ContractualEvidenceName.CURRENT_SPEED, 1000),
    )

    conclusions = SpeedComparisonRule().evaluate(make_context(*evidence), ())

    expected_ids = tuple(item.evidence_id for item in evidence)
    assert all(
        conclusion.justification.evidence_ids == expected_ids
        for conclusion in conclusions
    )


def test_contractual_rules_never_produce_candidate_domain_events() -> None:
    context = make_context(
        make_evidence(ContractualEvidenceName.PREVIOUS_SPEED, 500),
        make_evidence(ContractualEvidenceName.CURRENT_SPEED, 1000),
    )

    conclusions = SpeedComparisonRule().evaluate(context, ())

    assert all(isinstance(item, EvaluationConclusion) for item in conclusions)
    assert not any(isinstance(item, CandidateDomainEvent) for item in conclusions)
    assert all(item.kind is ConclusionKind.DERIVED_FACT for item in conclusions)
