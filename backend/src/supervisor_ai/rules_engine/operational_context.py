from supervisor_ai.rules_engine._conclusion_resolution import (
    ResolvedConclusionGroup,
    resolve_exclusive_conclusion_group,
)
from supervisor_ai.rules_engine.conclusion_names import (
    OperationalDecisionName,
    OperationalFactName,
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


def _build_decision(
    *,
    rule_id: str,
    name: OperationalDecisionName,
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
            summary=f"Operational decision '{name}' evaluated as '{status.value}'.",
            supporting_conclusion_ids=tuple(sorted(supporting_ids)),
        ),
        value=value,
    )


def _classify_exclusive_fact(
    *,
    rule_id: str,
    available: tuple[EvaluationConclusion, ...],
    positive_mapping: dict[str, OperationalDecisionName],
    source_not_evaluable: str,
    source_inconsistent: str,
    target_not_evaluable: OperationalDecisionName,
    target_inconsistent: OperationalDecisionName,
) -> tuple[EvaluationConclusion, ...]:
    resolved = resolve_exclusive_conclusion_group(
        available,
        positive_names=frozenset(positive_mapping),
        not_evaluable_name=source_not_evaluable,
        inconsistent_name=source_inconsistent,
    )
    if resolved.status is ConclusionStatus.INCONSISTENT:
        name = target_inconsistent
    elif resolved.status is ConclusionStatus.NOT_EVALUABLE:
        name = target_not_evaluable
    else:
        selected = resolved.selected[0]
        return (
            _build_decision(
                rule_id=rule_id,
                name=positive_mapping[selected.name],
                status=ConclusionStatus.TRUE,
                supporting_ids=resolved.supporting_ids,
                value=selected.value,
            ),
        )
    return (
        _build_decision(
            rule_id=rule_id,
            name=name,
            status=resolved.status,
            supporting_ids=resolved.supporting_ids,
        ),
    )


class TicketPresenceRule:
    """Classifica apenas a existência do ticket associado ao evento."""

    rule_id = "operational.ticket_presence"
    phase = RulePhase.AUTHORSHIP_AND_ELIGIBILITY

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        return _classify_exclusive_fact(
            rule_id=self.rule_id,
            available=available_conclusions,
            positive_mapping={
                OperationalFactName.TICKET_FOUND: (
                    OperationalDecisionName.TICKET_PRESENT
                ),
                OperationalFactName.TICKET_NOT_FOUND: (
                    OperationalDecisionName.TICKET_MISSING
                ),
            },
            source_not_evaluable=OperationalFactName.TICKET_LOOKUP_NOT_EVALUABLE,
            source_inconsistent=OperationalFactName.TICKET_LOOKUP_INCONSISTENT,
            target_not_evaluable=OperationalDecisionName.TICKET_PRESENCE_NOT_EVALUABLE,
            target_inconsistent=OperationalDecisionName.TICKET_PRESENCE_INCONSISTENT,
        )


class TicketSupportRule:
    """Classifica a área responsável pela abertura do ticket."""

    rule_id = "operational.ticket_support"
    phase = RulePhase.AUTHORSHIP_AND_ELIGIBILITY

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        return _classify_exclusive_fact(
            rule_id=self.rule_id,
            available=available_conclusions,
            positive_mapping={
                OperationalFactName.TICKET_OPENED_BY_SUPPORT: (
                    OperationalDecisionName.SUPPORT_TICKET
                ),
                OperationalFactName.TICKET_OPENED_OUTSIDE_SUPPORT: (
                    OperationalDecisionName.NON_SUPPORT_TICKET
                ),
            },
            source_not_evaluable=OperationalFactName.TICKET_AREA_NOT_EVALUABLE,
            source_inconsistent=OperationalFactName.TICKET_AREA_INCONSISTENT,
            target_not_evaluable=OperationalDecisionName.TICKET_SUPPORT_NOT_EVALUABLE,
            target_inconsistent=OperationalDecisionName.TICKET_SUPPORT_INCONSISTENT,
        )


class CommercialAuthorRule:
    """Deriva a autoria comercial exclusivamente do autor do ticket."""

    rule_id = "operational.commercial_author"
    phase = RulePhase.AUTHORSHIP_AND_ELIGIBILITY

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        return _classify_exclusive_fact(
            rule_id=self.rule_id,
            available=available_conclusions,
            positive_mapping={
                OperationalFactName.TICKET_AUTHOR_IDENTIFIED: (
                    OperationalDecisionName.COMMERCIAL_AUTHOR_IDENTIFIED
                ),
                OperationalFactName.TICKET_AUTHOR_MISSING: (
                    OperationalDecisionName.COMMERCIAL_AUTHOR_MISSING
                ),
            },
            source_not_evaluable=(
                OperationalFactName.TICKET_AUTHORSHIP_NOT_EVALUABLE
            ),
            source_inconsistent=OperationalFactName.TICKET_AUTHORSHIP_INCONSISTENT,
            target_not_evaluable=OperationalDecisionName.COMMERCIAL_AUTHOR_NOT_EVALUABLE,
            target_inconsistent=OperationalDecisionName.COMMERCIAL_AUTHOR_INCONSISTENT,
        )


class DuplicateAuthorRule:
    """Classifica a existência de autores concorrentes para o mesmo evento."""

    rule_id = "operational.duplicate_author"
    phase = RulePhase.AUTHORSHIP_AND_ELIGIBILITY

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        return _classify_exclusive_fact(
            rule_id=self.rule_id,
            available=available_conclusions,
            positive_mapping={
                OperationalFactName.DUPLICATE_AUTHOR_DETECTED: (
                    OperationalDecisionName.DUPLICATE_AUTHOR
                ),
                OperationalFactName.DUPLICATE_AUTHOR_NOT_DETECTED: (
                    OperationalDecisionName.NO_DUPLICATE_AUTHOR
                ),
            },
            source_not_evaluable=OperationalFactName.DUPLICATE_AUTHOR_NOT_EVALUABLE,
            source_inconsistent=OperationalFactName.DUPLICATE_AUTHOR_INCONSISTENT,
            target_not_evaluable=OperationalDecisionName.DUPLICATE_AUTHOR_NOT_EVALUABLE,
            target_inconsistent=OperationalDecisionName.DUPLICATE_AUTHOR_INCONSISTENT,
        )


class ManualReviewRule:
    """Solicita revisão humana somente quando há autoria duplicada."""

    rule_id = "operational.manual_review"
    phase = RulePhase.AUTHORSHIP_AND_ELIGIBILITY

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        resolved = _resolve_duplicate_author(available_conclusions)
        if resolved.status is ConclusionStatus.INCONSISTENT:
            return (
                _build_decision(
                    rule_id=self.rule_id,
                    name=OperationalDecisionName.MANUAL_REVIEW_INCONSISTENT,
                    status=resolved.status,
                    supporting_ids=resolved.supporting_ids,
                ),
            )
        if resolved.status is ConclusionStatus.NOT_EVALUABLE:
            return (
                _build_decision(
                    rule_id=self.rule_id,
                    name=OperationalDecisionName.MANUAL_REVIEW_NOT_EVALUABLE,
                    status=resolved.status,
                    supporting_ids=resolved.supporting_ids,
                ),
            )
        if resolved.selected[0].name == OperationalDecisionName.NO_DUPLICATE_AUTHOR:
            return ()
        return (
            _build_decision(
                rule_id=self.rule_id,
                name=OperationalDecisionName.MANUAL_REVIEW_REQUIRED,
                status=ConclusionStatus.TRUE,
                supporting_ids=resolved.supporting_ids,
                value=resolved.selected[0].value,
            ),
        )


def _resolve_duplicate_author(
    available: tuple[EvaluationConclusion, ...],
) -> ResolvedConclusionGroup:
    return resolve_exclusive_conclusion_group(
        available,
        positive_names=frozenset(
            {
                OperationalDecisionName.DUPLICATE_AUTHOR,
                OperationalDecisionName.NO_DUPLICATE_AUTHOR,
            }
        ),
        not_evaluable_name=OperationalDecisionName.DUPLICATE_AUTHOR_NOT_EVALUABLE,
        inconsistent_name=OperationalDecisionName.DUPLICATE_AUTHOR_INCONSISTENT,
    )


class OperationalContextEligibilityRule:
    """Avalia somente a suficiência e elegibilidade do contexto operacional."""

    rule_id = "operational.context_eligibility"
    phase = RulePhase.AUTHORSHIP_AND_ELIGIBILITY

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context
        ticket = resolve_exclusive_conclusion_group(
            available_conclusions,
            positive_names=frozenset(
                {
                    OperationalDecisionName.TICKET_PRESENT,
                    OperationalDecisionName.TICKET_MISSING,
                }
            ),
            not_evaluable_name=(
                OperationalDecisionName.TICKET_PRESENCE_NOT_EVALUABLE
            ),
            inconsistent_name=OperationalDecisionName.TICKET_PRESENCE_INCONSISTENT,
        )
        support = resolve_exclusive_conclusion_group(
            available_conclusions,
            positive_names=frozenset(
                {
                    OperationalDecisionName.SUPPORT_TICKET,
                    OperationalDecisionName.NON_SUPPORT_TICKET,
                }
            ),
            not_evaluable_name=OperationalDecisionName.TICKET_SUPPORT_NOT_EVALUABLE,
            inconsistent_name=OperationalDecisionName.TICKET_SUPPORT_INCONSISTENT,
        )
        author = resolve_exclusive_conclusion_group(
            available_conclusions,
            positive_names=frozenset(
                {
                    OperationalDecisionName.COMMERCIAL_AUTHOR_IDENTIFIED,
                    OperationalDecisionName.COMMERCIAL_AUTHOR_MISSING,
                }
            ),
            not_evaluable_name=(
                OperationalDecisionName.COMMERCIAL_AUTHOR_NOT_EVALUABLE
            ),
            inconsistent_name=OperationalDecisionName.COMMERCIAL_AUTHOR_INCONSISTENT,
        )
        duplicate = _resolve_duplicate_author(available_conclusions)
        groups = (ticket, support, author, duplicate)
        supporting_ids = tuple(
            sorted(
                identifier for group in groups for identifier in group.supporting_ids
            )
        )

        if any(group.status is ConclusionStatus.INCONSISTENT for group in groups):
            return (
                _build_decision(
                    rule_id=self.rule_id,
                    name=OperationalDecisionName.OPERATIONAL_CONTEXT_INCONSISTENT,
                    status=ConclusionStatus.INCONSISTENT,
                    supporting_ids=supporting_ids,
                ),
            )

        selected = {group.selected[0].name for group in groups if group.selected}
        ineligible = {
            OperationalDecisionName.TICKET_MISSING,
            OperationalDecisionName.NON_SUPPORT_TICKET,
            OperationalDecisionName.COMMERCIAL_AUTHOR_MISSING,
        }
        if selected & ineligible:
            return (
                _build_decision(
                    rule_id=self.rule_id,
                    name=OperationalDecisionName.OPERATIONAL_CONTEXT_INELIGIBLE,
                    status=ConclusionStatus.TRUE,
                    supporting_ids=supporting_ids,
                ),
            )

        if (
            any(group.status is ConclusionStatus.NOT_EVALUABLE for group in groups)
            or OperationalDecisionName.DUPLICATE_AUTHOR in selected
        ):
            return (
                _build_decision(
                    rule_id=self.rule_id,
                    name=OperationalDecisionName.OPERATIONAL_CONTEXT_NOT_EVALUABLE,
                    status=ConclusionStatus.NOT_EVALUABLE,
                    supporting_ids=supporting_ids,
                ),
            )

        required = {
            OperationalDecisionName.TICKET_PRESENT,
            OperationalDecisionName.SUPPORT_TICKET,
            OperationalDecisionName.COMMERCIAL_AUTHOR_IDENTIFIED,
            OperationalDecisionName.NO_DUPLICATE_AUTHOR,
        }
        name = (
            OperationalDecisionName.OPERATIONAL_CONTEXT_ELIGIBLE
            if required <= selected
            else OperationalDecisionName.OPERATIONAL_CONTEXT_NOT_EVALUABLE
        )
        status = (
            ConclusionStatus.TRUE
            if name is OperationalDecisionName.OPERATIONAL_CONTEXT_ELIGIBLE
            else ConclusionStatus.NOT_EVALUABLE
        )
        return (
            _build_decision(
                rule_id=self.rule_id,
                name=name,
                status=status,
                supporting_ids=supporting_ids,
            ),
        )
