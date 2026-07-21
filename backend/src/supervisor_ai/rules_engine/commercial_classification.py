from supervisor_ai.rules_engine._conclusion_resolution import (
    ResolvedConclusionGroup,
    has_duplicate_names,
    relevant_conclusions,
    resolve_exclusive_conclusion_group,
)
from supervisor_ai.rules_engine.conclusion_names import (
    CommercialClassificationName,
    ContractualFactName,
)
from supervisor_ai.rules_engine.types import (
    ConclusionKind,
    ConclusionStatus,
    EvaluationConclusion,
    EvaluationContext,
    EvidenceValue,
    Justification,
    RulePhase,
)


def _resolve_additionals(
    available: tuple[EvaluationConclusion, ...],
) -> ResolvedConclusionGroup:
    positive_names = frozenset(
        {
            ContractualFactName.COMMON_ADDITIONAL_INCLUDED,
            ContractualFactName.COMMON_ADDITIONAL_REMOVED,
            ContractualFactName.COMMON_ADDITIONALS_UNCHANGED,
        }
    )
    all_names = positive_names | {
        ContractualFactName.COMMON_ADDITIONALS_NOT_EVALUABLE,
        ContractualFactName.COMMON_ADDITIONALS_INCONSISTENT,
    }
    relevant = relevant_conclusions(available, all_names)
    supporting_ids = tuple(item.conclusion_id for item in relevant)

    if has_duplicate_names(relevant):
        return ResolvedConclusionGroup(
            ConclusionStatus.INCONSISTENT,
            supporting_ids=supporting_ids,
        )
    if any(
        item.name == ContractualFactName.COMMON_ADDITIONALS_INCONSISTENT
        or item.status is ConclusionStatus.INCONSISTENT
        for item in relevant
    ):
        return ResolvedConclusionGroup(
            ConclusionStatus.INCONSISTENT,
            supporting_ids=supporting_ids,
        )
    if any(
        item.name == ContractualFactName.COMMON_ADDITIONALS_NOT_EVALUABLE
        or item.status is ConclusionStatus.NOT_EVALUABLE
        for item in relevant
    ):
        return ResolvedConclusionGroup(
            ConclusionStatus.NOT_EVALUABLE,
            supporting_ids=supporting_ids,
        )
    if any(item.status is not ConclusionStatus.TRUE for item in relevant):
        return ResolvedConclusionGroup(
            ConclusionStatus.INCONSISTENT,
            supporting_ids=supporting_ids,
        )

    selected = tuple(item for item in relevant if item.name in positive_names)
    if not selected:
        return ResolvedConclusionGroup(
            ConclusionStatus.NOT_EVALUABLE,
            supporting_ids=supporting_ids,
        )

    selected_names = {item.name for item in selected}
    unchanged_with_change = (
        ContractualFactName.COMMON_ADDITIONALS_UNCHANGED in selected_names
        and len(selected_names) > 1
    )
    if unchanged_with_change:
        return ResolvedConclusionGroup(
            ConclusionStatus.INCONSISTENT,
            supporting_ids=supporting_ids,
        )
    return ResolvedConclusionGroup(
        ConclusionStatus.TRUE,
        selected=selected,
        supporting_ids=supporting_ids,
    )


def _build_decision(
    *,
    rule_id: str,
    name: CommercialClassificationName,
    status: ConclusionStatus,
    supporting_ids: tuple[str, ...],
    value: EvidenceValue = None,
) -> EvaluationConclusion:
    return EvaluationConclusion(
        conclusion_id=f"{rule_id}.{name}",
        name=name,
        kind=ConclusionKind.DOMAIN_DECISION,
        status=status,
        justification=Justification(
            rule_id=rule_id,
            summary=(
                f"Commercial classification '{name}' evaluated as '{status.value}'."
            ),
            supporting_conclusion_ids=supporting_ids,
        ),
        value=value,
    )


def _error_decision(
    *,
    rule_id: str,
    resolved: tuple[ResolvedConclusionGroup, ...],
    not_evaluable_name: CommercialClassificationName,
    inconsistent_name: CommercialClassificationName,
) -> tuple[EvaluationConclusion, ...] | None:
    supporting_ids = tuple(
        sorted(
            conclusion_id
            for group in resolved
            for conclusion_id in group.supporting_ids
        )
    )
    if any(group.status is ConclusionStatus.INCONSISTENT for group in resolved):
        return (
            _build_decision(
                rule_id=rule_id,
                name=inconsistent_name,
                status=ConclusionStatus.INCONSISTENT,
                supporting_ids=supporting_ids,
            ),
        )
    if any(group.status is ConclusionStatus.NOT_EVALUABLE for group in resolved):
        return (
            _build_decision(
                rule_id=rule_id,
                name=not_evaluable_name,
                status=ConclusionStatus.NOT_EVALUABLE,
                supporting_ids=supporting_ids,
            ),
        )
    return None


class PlanChangeClassificationRule:
    """Classifica mudança de plano usando somente fatos da Fase A."""

    rule_id = "commercial.plan_change_classification"
    phase = RulePhase.COMMERCIAL_CLASSIFICATION

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        speed = resolve_exclusive_conclusion_group(
            available_conclusions,
            positive_names=frozenset(
                {
                    ContractualFactName.SPEED_INCREASED,
                    ContractualFactName.SPEED_DECREASED,
                    ContractualFactName.SPEED_UNCHANGED,
                }
            ),
            not_evaluable_name=ContractualFactName.SPEED_NOT_EVALUABLE,
            inconsistent_name=ContractualFactName.SPEED_INCONSISTENT,
        )
        modality = resolve_exclusive_conclusion_group(
            available_conclusions,
            positive_names=frozenset(
                {
                    ContractualFactName.PLAN_MODALITY_CHANGED,
                    ContractualFactName.PLAN_MODALITY_UNCHANGED,
                }
            ),
            not_evaluable_name=ContractualFactName.PLAN_MODALITY_NOT_EVALUABLE,
            inconsistent_name=ContractualFactName.PLAN_MODALITY_INCONSISTENT,
        )
        mesh = resolve_exclusive_conclusion_group(
            available_conclusions,
            positive_names=frozenset(
                {
                    ContractualFactName.MESH_INCLUDED,
                    ContractualFactName.MESH_REMOVED,
                    ContractualFactName.MESH_UNCHANGED,
                }
            ),
            not_evaluable_name=ContractualFactName.MESH_NOT_EVALUABLE,
            inconsistent_name=ContractualFactName.MESH_INCONSISTENT,
        )
        groups = (speed, modality, mesh)
        error = _error_decision(
            rule_id=self.rule_id,
            resolved=groups,
            not_evaluable_name=CommercialClassificationName.PLAN_CHANGE_NOT_EVALUABLE,
            inconsistent_name=CommercialClassificationName.PLAN_CHANGE_INCONSISTENT,
        )
        if error is not None:
            return error

        selected = tuple(group.selected[0] for group in groups)
        change_names = {
            ContractualFactName.SPEED_INCREASED,
            ContractualFactName.SPEED_DECREASED,
            ContractualFactName.PLAN_MODALITY_CHANGED,
            ContractualFactName.MESH_INCLUDED,
            ContractualFactName.MESH_REMOVED,
        }
        changed = any(item.name in change_names for item in selected)
        return (
            _build_decision(
                rule_id=self.rule_id,
                name=CommercialClassificationName.PLAN_CHANGED
                if changed
                else CommercialClassificationName.PLAN_UNCHANGED,
                status=ConclusionStatus.TRUE,
                supporting_ids=tuple(sorted(item.conclusion_id for item in selected)),
                value=tuple(item.name for item in selected),
            ),
        )


class RecurringRevenueClassificationRule:
    """Classifica a direção comercial usando o fato recorrente consolidado."""

    rule_id = "commercial.recurring_revenue_classification"
    phase = RulePhase.COMMERCIAL_CLASSIFICATION

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        revenue = resolve_exclusive_conclusion_group(
            available_conclusions,
            positive_names=frozenset(
                {
                    ContractualFactName.RECURRING_VALUE_INCREASED,
                    ContractualFactName.RECURRING_VALUE_DECREASED,
                    ContractualFactName.RECURRING_VALUE_UNCHANGED,
                }
            ),
            not_evaluable_name=ContractualFactName.RECURRING_VALUE_NOT_EVALUABLE,
            inconsistent_name=ContractualFactName.RECURRING_VALUE_INCONSISTENT,
        )
        error = _error_decision(
            rule_id=self.rule_id,
            resolved=(revenue,),
            not_evaluable_name=(
                CommercialClassificationName.RECURRING_REVENUE_NOT_EVALUABLE
            ),
            inconsistent_name=(
                CommercialClassificationName.RECURRING_REVENUE_INCONSISTENT
            ),
        )
        if error is not None:
            return error

        source = revenue.selected[0]
        names = {
            ContractualFactName.RECURRING_VALUE_INCREASED: (
                CommercialClassificationName.COMMERCIAL_UPGRADE
            ),
            ContractualFactName.RECURRING_VALUE_DECREASED: (
                CommercialClassificationName.COMMERCIAL_DOWNGRADE
            ),
            ContractualFactName.RECURRING_VALUE_UNCHANGED: (
                CommercialClassificationName.RECURRING_REVENUE_UNCHANGED
            ),
        }
        return (
            _build_decision(
                rule_id=self.rule_id,
                name=names[ContractualFactName(source.name)],
                status=ConclusionStatus.TRUE,
                supporting_ids=(source.conclusion_id,),
                value=source.value,
            ),
        )


class CommonAdditionalClassificationRule:
    """Classifica inclusões e remoções de adicionais comuns."""

    rule_id = "commercial.common_additional_classification"
    phase = RulePhase.COMMERCIAL_CLASSIFICATION

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        additionals = _resolve_additionals(available_conclusions)
        error = _error_decision(
            rule_id=self.rule_id,
            resolved=(additionals,),
            not_evaluable_name=(
                CommercialClassificationName.COMMON_ADDITIONAL_CLASSIFICATION_NOT_EVALUABLE
            ),
            inconsistent_name=(
                CommercialClassificationName.COMMON_ADDITIONAL_CLASSIFICATION_INCONSISTENT
            ),
        )
        if error is not None:
            return error

        decisions: list[EvaluationConclusion] = []
        for source in additionals.selected:
            if source.name == ContractualFactName.COMMON_ADDITIONAL_INCLUDED:
                name = CommercialClassificationName.COMMON_ADDITIONAL_SALE
            elif source.name == ContractualFactName.COMMON_ADDITIONAL_REMOVED:
                name = CommercialClassificationName.COMMON_ADDITIONAL_REMOVAL
            else:
                continue
            decisions.append(
                _build_decision(
                    rule_id=self.rule_id,
                    name=name,
                    status=ConclusionStatus.TRUE,
                    supporting_ids=(source.conclusion_id,),
                    value=source.value,
                )
            )
        return tuple(decisions)


class OperationScopeClassificationRule:
    """Distingue operações adicionais puras de operações mistas."""

    rule_id = "commercial.operation_scope_classification"
    phase = RulePhase.COMMERCIAL_CLASSIFICATION

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        plan = resolve_exclusive_conclusion_group(
            available_conclusions,
            positive_names=frozenset(
                {
                    CommercialClassificationName.PLAN_CHANGED,
                    CommercialClassificationName.PLAN_UNCHANGED,
                }
            ),
            not_evaluable_name=(CommercialClassificationName.PLAN_CHANGE_NOT_EVALUABLE),
            inconsistent_name=(CommercialClassificationName.PLAN_CHANGE_INCONSISTENT),
        )
        additionals = _resolve_additionals(available_conclusions)
        groups = (plan, additionals)
        error = _error_decision(
            rule_id=self.rule_id,
            resolved=groups,
            not_evaluable_name=(
                CommercialClassificationName.OPERATION_SCOPE_NOT_EVALUABLE
            ),
            inconsistent_name=(
                CommercialClassificationName.OPERATION_SCOPE_INCONSISTENT
            ),
        )
        if error is not None:
            return error

        changed_additionals = tuple(
            item
            for item in additionals.selected
            if item.name
            in {
                ContractualFactName.COMMON_ADDITIONAL_INCLUDED,
                ContractualFactName.COMMON_ADDITIONAL_REMOVED,
            }
        )
        if not changed_additionals:
            return ()

        plan_conclusion = plan.selected[0]
        mixed = plan_conclusion.name == CommercialClassificationName.PLAN_CHANGED
        supporting_ids = tuple(
            sorted(
                (plan_conclusion.conclusion_id,)
                + tuple(item.conclusion_id for item in changed_additionals)
            )
        )
        return (
            _build_decision(
                rule_id=self.rule_id,
                name=(
                    CommercialClassificationName.MIXED_PLAN_AND_ADDITIONAL_OPERATION
                    if mixed
                    else CommercialClassificationName.ADDITIONAL_ONLY_OPERATION
                ),
                status=ConclusionStatus.TRUE,
                supporting_ids=supporting_ids,
            ),
        )
