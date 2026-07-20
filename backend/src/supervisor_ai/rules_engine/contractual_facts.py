from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from supervisor_ai.rules_engine.contractual_evidence import (
    ContractualEvidenceName,
)
from supervisor_ai.rules_engine.types import (
    ConclusionKind,
    ConclusionStatus,
    EvaluationConclusion,
    EvaluationContext,
    Evidence,
    EvidenceValue,
    Justification,
    RulePhase,
)

_MESH_NAME = "mesh"


@dataclass(frozen=True, slots=True)
class _ResolvedPair:
    status: ConclusionStatus
    previous: EvidenceValue = None
    current: EvidenceValue = None
    evidence_ids: tuple[str, ...] = ()


def _matching_evidence(
    context: EvaluationContext,
    name: ContractualEvidenceName,
) -> tuple[Evidence, ...]:
    return tuple(item for item in context.evidence if item.name == name)


def _resolve_value(
    context: EvaluationContext,
    name: ContractualEvidenceName,
    is_valid: Callable[[EvidenceValue], bool],
) -> tuple[ConclusionStatus, EvidenceValue, tuple[str, ...]]:
    matches = _matching_evidence(context, name)
    if not matches:
        return ConclusionStatus.NOT_EVALUABLE, None, ()

    evidence_ids = tuple(item.evidence_id for item in matches)
    if any(not is_valid(item.value) for item in matches):
        return ConclusionStatus.INCONSISTENT, None, evidence_ids

    first_value = matches[0].value
    if any(item.value != first_value for item in matches[1:]):
        return ConclusionStatus.INCONSISTENT, None, evidence_ids

    return ConclusionStatus.TRUE, first_value, evidence_ids


def _resolve_pair(
    context: EvaluationContext,
    previous_name: ContractualEvidenceName,
    current_name: ContractualEvidenceName,
    is_valid: Callable[[EvidenceValue], bool],
) -> _ResolvedPair:
    previous_status, previous, previous_ids = _resolve_value(
        context, previous_name, is_valid
    )
    current_status, current, current_ids = _resolve_value(
        context, current_name, is_valid
    )
    evidence_ids = previous_ids + current_ids

    if ConclusionStatus.INCONSISTENT in (previous_status, current_status):
        return _ResolvedPair(ConclusionStatus.INCONSISTENT, evidence_ids=evidence_ids)
    if ConclusionStatus.NOT_EVALUABLE in (previous_status, current_status):
        return _ResolvedPair(ConclusionStatus.NOT_EVALUABLE, evidence_ids=evidence_ids)
    return _ResolvedPair(
        ConclusionStatus.TRUE,
        previous=previous,
        current=current,
        evidence_ids=evidence_ids,
    )


def _build_conclusion(
    *,
    rule_id: str,
    name: str,
    status: ConclusionStatus,
    evidence_ids: tuple[str, ...],
    value: EvidenceValue = None,
) -> EvaluationConclusion:
    return EvaluationConclusion(
        conclusion_id=f"{rule_id}.{name}",
        name=name,
        kind=ConclusionKind.DERIVED_FACT,
        status=status,
        justification=Justification(
            rule_id=rule_id,
            summary=f"Contractual fact '{name}' evaluated as '{status.value}'.",
            evidence_ids=evidence_ids,
        ),
        value=value,
    )


def _comparison_conclusions(
    *,
    rule_id: str,
    pair: _ResolvedPair,
    increased_name: str,
    decreased_name: str,
    unchanged_name: str,
    not_evaluable_name: str,
    inconsistent_name: str,
) -> tuple[EvaluationConclusion, ...]:
    if pair.status is not ConclusionStatus.TRUE:
        name = (
            not_evaluable_name
            if pair.status is ConclusionStatus.NOT_EVALUABLE
            else inconsistent_name
        )
        return (
            _build_conclusion(
                rule_id=rule_id,
                name=name,
                status=pair.status,
                evidence_ids=pair.evidence_ids,
            ),
        )

    value = (pair.previous, pair.current)
    if pair.current > pair.previous:  # type: ignore[operator]
        name = increased_name
    elif pair.current < pair.previous:  # type: ignore[operator]
        name = decreased_name
    else:
        name = unchanged_name
    return (
        _build_conclusion(
            rule_id=rule_id,
            name=name,
            status=ConclusionStatus.TRUE,
            evidence_ids=pair.evidence_ids,
            value=value,
        ),
    )


class SpeedComparisonRule:
    """Compara somente as velocidades contratuais observadas."""

    rule_id = "contractual.speed_comparison"
    phase = RulePhase.CONTRACTUAL_FACTS

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del available_conclusions
        pair = _resolve_pair(
            context,
            ContractualEvidenceName.PREVIOUS_SPEED,
            ContractualEvidenceName.CURRENT_SPEED,
            lambda value: type(value) is int,
        )
        return _comparison_conclusions(
            rule_id=self.rule_id,
            pair=pair,
            increased_name="speed_increased",
            decreased_name="speed_decreased",
            unchanged_name="speed_unchanged",
            not_evaluable_name="speed_not_evaluable",
            inconsistent_name="speed_inconsistent",
        )


class PlanModalityComparisonRule:
    """Compara somente as modalidades comerciais observadas."""

    rule_id = "contractual.plan_modality_comparison"
    phase = RulePhase.CONTRACTUAL_FACTS

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del available_conclusions
        pair = _resolve_pair(
            context,
            ContractualEvidenceName.PREVIOUS_PLAN_MODALITY,
            ContractualEvidenceName.CURRENT_PLAN_MODALITY,
            lambda value: type(value) is str,
        )
        if pair.status is not ConclusionStatus.TRUE:
            name = (
                "plan_modality_not_evaluable"
                if pair.status is ConclusionStatus.NOT_EVALUABLE
                else "plan_modality_inconsistent"
            )
            return (
                _build_conclusion(
                    rule_id=self.rule_id,
                    name=name,
                    status=pair.status,
                    evidence_ids=pair.evidence_ids,
                ),
            )

        value = (pair.previous, pair.current)
        changed = pair.previous != pair.current
        return (
            _build_conclusion(
                rule_id=self.rule_id,
                name="plan_modality_changed"
                if changed
                else "plan_modality_unchanged",
                status=ConclusionStatus.TRUE,
                evidence_ids=pair.evidence_ids,
                value=value,
            ),
        )


class MeshComparisonRule:
    """Compara somente a situação do Mesh, separada de adicionais comuns."""

    rule_id = "contractual.mesh_comparison"
    phase = RulePhase.CONTRACTUAL_FACTS

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del available_conclusions
        pair = _resolve_pair(
            context,
            ContractualEvidenceName.PREVIOUS_MESH_ENABLED,
            ContractualEvidenceName.CURRENT_MESH_ENABLED,
            lambda value: type(value) is bool,
        )
        if pair.status is not ConclusionStatus.TRUE:
            name = (
                "mesh_not_evaluable"
                if pair.status is ConclusionStatus.NOT_EVALUABLE
                else "mesh_inconsistent"
            )
            return (
                _build_conclusion(
                    rule_id=self.rule_id,
                    name=name,
                    status=pair.status,
                    evidence_ids=pair.evidence_ids,
                ),
            )

        previous = cast(bool, pair.previous)
        current = cast(bool, pair.current)
        value = (previous, current)
        if not previous and current:
            name = "mesh_included"
        elif previous and not current:
            name = "mesh_removed"
        else:
            name = "mesh_unchanged"
        return (
            _build_conclusion(
                rule_id=self.rule_id,
                name=name,
                status=ConclusionStatus.TRUE,
                evidence_ids=pair.evidence_ids,
                value=value,
            ),
        )


def _is_valid_additionals(value: EvidenceValue) -> bool:
    if not isinstance(value, tuple):
        return False
    if any(type(item) is not str for item in value):
        return False
    return len(value) == len(set(value))


def _without_mesh(additionals: tuple[str, ...]) -> frozenset[str]:
    return frozenset(
        item for item in additionals if item.strip().casefold() != _MESH_NAME
    )


class CommonAdditionalsComparisonRule:
    """Compara adicionais comuns sem incluir Mesh nessa dimensão."""

    rule_id = "contractual.common_additionals_comparison"
    phase = RulePhase.CONTRACTUAL_FACTS

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del available_conclusions
        pair = _resolve_pair(
            context,
            ContractualEvidenceName.PREVIOUS_ADDITIONALS,
            ContractualEvidenceName.CURRENT_ADDITIONALS,
            _is_valid_additionals,
        )
        if pair.status is not ConclusionStatus.TRUE:
            name = (
                "common_additionals_not_evaluable"
                if pair.status is ConclusionStatus.NOT_EVALUABLE
                else "common_additionals_inconsistent"
            )
            return (
                _build_conclusion(
                    rule_id=self.rule_id,
                    name=name,
                    status=pair.status,
                    evidence_ids=pair.evidence_ids,
                ),
            )

        previous = _without_mesh(cast(tuple[str, ...], pair.previous))
        current = _without_mesh(cast(tuple[str, ...], pair.current))
        included = tuple(sorted(current - previous))
        removed = tuple(sorted(previous - current))
        conclusions: list[EvaluationConclusion] = []
        if included:
            conclusions.append(
                _build_conclusion(
                    rule_id=self.rule_id,
                    name="common_additional_included",
                    status=ConclusionStatus.TRUE,
                    evidence_ids=pair.evidence_ids,
                    value=included,
                )
            )
        if removed:
            conclusions.append(
                _build_conclusion(
                    rule_id=self.rule_id,
                    name="common_additional_removed",
                    status=ConclusionStatus.TRUE,
                    evidence_ids=pair.evidence_ids,
                    value=removed,
                )
            )
        if not conclusions:
            conclusions.append(
                _build_conclusion(
                    rule_id=self.rule_id,
                    name="common_additionals_unchanged",
                    status=ConclusionStatus.TRUE,
                    evidence_ids=pair.evidence_ids,
                    value=tuple(sorted(current)),
                )
            )
        return tuple(conclusions)


class RecurringValueComparisonRule:
    """Compara valores recorrentes usando exclusivamente ``Decimal``."""

    rule_id = "contractual.recurring_value_comparison"
    phase = RulePhase.CONTRACTUAL_FACTS

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del available_conclusions
        pair = _resolve_pair(
            context,
            ContractualEvidenceName.PREVIOUS_RECURRING_VALUE,
            ContractualEvidenceName.CURRENT_RECURRING_VALUE,
            lambda value: type(value) is Decimal,
        )
        return _comparison_conclusions(
            rule_id=self.rule_id,
            pair=pair,
            increased_name="recurring_value_increased",
            decreased_name="recurring_value_decreased",
            unchanged_name="recurring_value_unchanged",
            not_evaluable_name="recurring_value_not_evaluable",
            inconsistent_name="recurring_value_inconsistent",
        )
