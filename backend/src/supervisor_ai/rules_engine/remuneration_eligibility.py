from dataclasses import dataclass
from enum import StrEnum

from supervisor_ai.rules_engine._conclusion_resolution import (
    ResolvedConclusionGroup,
    has_duplicate_names,
    relevant_conclusions,
    resolve_exclusive_conclusion_group,
)
from supervisor_ai.rules_engine.conclusion_names import (
    CommercialClassificationName,
    OperationalDecisionName,
)
from supervisor_ai.rules_engine.types import ConclusionStatus, EvaluationConclusion


class RemunerationEligibilityStatus(StrEnum):
    """Estados possíveis antes de qualquer validação financeira."""

    POTENTIALLY_ELIGIBLE = "potentially_eligible"
    NOT_ELIGIBLE = "not_eligible"
    PENDING_MANUAL_REVIEW = "pending_manual_review"
    NOT_EVALUABLE = "not_evaluable"


class RemunerationEligibilityReason(StrEnum):
    """Motivos estáveis e auditáveis da decisão de elegibilidade."""

    NO_COMMERCIAL_EVENT = "no_commercial_event"
    DOWNGRADE = "downgrade"
    NO_PLAN_CHANGE_TICKET = "no_plan_change_ticket"
    MISSING_TICKET_AUTHOR = "missing_ticket_author"
    TICKET_AUTHOR_NOT_SUPPORT = "ticket_author_not_support"
    ADMINISTRATIVE_CHANGE = "administrative_change"
    CORRECTIVE_CHANGE = "corrective_change"
    DUPLICATE_CLAIM = "duplicate_claim"
    AUTHORSHIP_CONFLICT = "authorship_conflict"
    INSUFFICIENT_DATA = "insufficient_data"
    INCONSISTENT_INPUT = "inconsistent_input"


@dataclass(frozen=True, slots=True)
class RemunerationEligibilityResult:
    """Resultado imutável da combinação das Fases B e C.

    As referências são separadas por fase para preservar rastreabilidade sem
    acoplar o contrato aos objetos internos das regras ou à persistência.
    """

    status: RemunerationEligibilityStatus
    reasons: tuple[RemunerationEligibilityReason, ...]
    commercial_conclusion_ids: tuple[str, ...]
    operational_conclusion_ids: tuple[str, ...]


def _resolve(
    available: tuple[EvaluationConclusion, ...],
    *,
    positive: frozenset[str],
    not_evaluable: str,
    inconsistent: str,
) -> ResolvedConclusionGroup:
    return resolve_exclusive_conclusion_group(
        available,
        positive_names=positive,
        not_evaluable_name=not_evaluable,
        inconsistent_name=inconsistent,
    )


def _result(
    status: RemunerationEligibilityStatus,
    reasons: tuple[RemunerationEligibilityReason, ...],
    commercial: tuple[str, ...],
    operational: tuple[str, ...],
) -> RemunerationEligibilityResult:
    return RemunerationEligibilityResult(
        status=status,
        reasons=reasons,
        commercial_conclusion_ids=tuple(sorted(commercial)),
        operational_conclusion_ids=tuple(sorted(operational)),
    )


class RemunerationEligibilityEvaluator:
    """Combina decisões das Fases B e C sem reavaliar suas regras."""

    def evaluate(
        self,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> RemunerationEligibilityResult:
        revenue = _resolve(
            available_conclusions,
            positive=frozenset(
                {
                    CommercialClassificationName.COMMERCIAL_UPGRADE,
                    CommercialClassificationName.COMMERCIAL_DOWNGRADE,
                    CommercialClassificationName.RECURRING_REVENUE_UNCHANGED,
                }
            ),
            not_evaluable=(
                CommercialClassificationName.RECURRING_REVENUE_NOT_EVALUABLE
            ),
            inconsistent=(CommercialClassificationName.RECURRING_REVENUE_INCONSISTENT),
        )
        ticket = _resolve(
            available_conclusions,
            positive=frozenset(
                {
                    OperationalDecisionName.TICKET_PRESENT,
                    OperationalDecisionName.TICKET_MISSING,
                }
            ),
            not_evaluable=OperationalDecisionName.TICKET_PRESENCE_NOT_EVALUABLE,
            inconsistent=OperationalDecisionName.TICKET_PRESENCE_INCONSISTENT,
        )
        support = _resolve(
            available_conclusions,
            positive=frozenset(
                {
                    OperationalDecisionName.SUPPORT_TICKET,
                    OperationalDecisionName.NON_SUPPORT_TICKET,
                }
            ),
            not_evaluable=OperationalDecisionName.TICKET_SUPPORT_NOT_EVALUABLE,
            inconsistent=OperationalDecisionName.TICKET_SUPPORT_INCONSISTENT,
        )
        author = _resolve(
            available_conclusions,
            positive=frozenset(
                {
                    OperationalDecisionName.COMMERCIAL_AUTHOR_IDENTIFIED,
                    OperationalDecisionName.COMMERCIAL_AUTHOR_MISSING,
                }
            ),
            not_evaluable=(OperationalDecisionName.COMMERCIAL_AUTHOR_NOT_EVALUABLE),
            inconsistent=OperationalDecisionName.COMMERCIAL_AUTHOR_INCONSISTENT,
        )
        duplicate = _resolve(
            available_conclusions,
            positive=frozenset(
                {
                    OperationalDecisionName.DUPLICATE_AUTHOR,
                    OperationalDecisionName.NO_DUPLICATE_AUTHOR,
                }
            ),
            not_evaluable=OperationalDecisionName.DUPLICATE_AUTHOR_NOT_EVALUABLE,
            inconsistent=OperationalDecisionName.DUPLICATE_AUTHOR_INCONSISTENT,
        )
        ticket_purpose = _resolve(
            available_conclusions,
            positive=frozenset(
                {
                    OperationalDecisionName.PLAN_CHANGE_TICKET,
                    OperationalDecisionName.NON_PLAN_CHANGE_TICKET,
                }
            ),
            not_evaluable=OperationalDecisionName.TICKET_PURPOSE_NOT_EVALUABLE,
            inconsistent=OperationalDecisionName.TICKET_PURPOSE_INCONSISTENT,
        )
        administrative = _resolve(
            available_conclusions,
            positive=frozenset(
                {
                    OperationalDecisionName.ADMINISTRATIVE_CHANGE,
                    OperationalDecisionName.NON_ADMINISTRATIVE_CHANGE,
                }
            ),
            not_evaluable=(OperationalDecisionName.ADMINISTRATIVE_NATURE_NOT_EVALUABLE),
            inconsistent=(OperationalDecisionName.ADMINISTRATIVE_NATURE_INCONSISTENT),
        )
        corrective = _resolve(
            available_conclusions,
            positive=frozenset(
                {
                    OperationalDecisionName.CORRECTIVE_CHANGE,
                    OperationalDecisionName.NON_CORRECTIVE_CHANGE,
                }
            ),
            not_evaluable=(OperationalDecisionName.CORRECTIVE_NATURE_NOT_EVALUABLE),
            inconsistent=OperationalDecisionName.CORRECTIVE_NATURE_INCONSISTENT,
        )
        conflict = _resolve(
            available_conclusions,
            positive=frozenset(
                {
                    OperationalDecisionName.AUTHORSHIP_CONFLICT,
                    OperationalDecisionName.NO_AUTHORSHIP_CONFLICT,
                }
            ),
            not_evaluable=(OperationalDecisionName.AUTHORSHIP_CONFLICT_NOT_EVALUABLE),
            inconsistent=(OperationalDecisionName.AUTHORSHIP_CONFLICT_INCONSISTENT),
        )
        additional = self._resolve_additional_sale(available_conclusions)
        groups = (
            revenue,
            additional,
            ticket,
            support,
            author,
            duplicate,
            ticket_purpose,
            administrative,
            corrective,
            conflict,
        )
        commercial_ids = revenue.supporting_ids + additional.supporting_ids
        operational_ids = tuple(
            identifier for group in groups[2:] for identifier in group.supporting_ids
        )

        if any(group.status is ConclusionStatus.INCONSISTENT for group in groups):
            return _result(
                RemunerationEligibilityStatus.NOT_EVALUABLE,
                (RemunerationEligibilityReason.INCONSISTENT_INPUT,),
                commercial_ids,
                operational_ids,
            )

        selected = {group.selected[0].name for group in groups if group.selected}
        if OperationalDecisionName.COMMERCIAL_AUTHOR_MISSING in selected:
            return _result(
                RemunerationEligibilityStatus.NOT_EVALUABLE,
                (RemunerationEligibilityReason.MISSING_TICKET_AUTHOR,),
                commercial_ids,
                operational_ids,
            )
        if any(group.status is ConclusionStatus.NOT_EVALUABLE for group in groups):
            return _result(
                RemunerationEligibilityStatus.NOT_EVALUABLE,
                (RemunerationEligibilityReason.INSUFFICIENT_DATA,),
                commercial_ids,
                operational_ids,
            )

        review_reasons: list[RemunerationEligibilityReason] = []
        if OperationalDecisionName.DUPLICATE_AUTHOR in selected:
            review_reasons.append(RemunerationEligibilityReason.DUPLICATE_CLAIM)
        if OperationalDecisionName.AUTHORSHIP_CONFLICT in selected:
            review_reasons.append(RemunerationEligibilityReason.AUTHORSHIP_CONFLICT)
        if review_reasons:
            return _result(
                RemunerationEligibilityStatus.PENDING_MANUAL_REVIEW,
                tuple(review_reasons),
                commercial_ids,
                operational_ids,
            )

        ineligible_reasons: list[RemunerationEligibilityReason] = []
        if OperationalDecisionName.ADMINISTRATIVE_CHANGE in selected:
            ineligible_reasons.append(
                RemunerationEligibilityReason.ADMINISTRATIVE_CHANGE
            )
        if OperationalDecisionName.CORRECTIVE_CHANGE in selected:
            ineligible_reasons.append(RemunerationEligibilityReason.CORRECTIVE_CHANGE)
        if CommercialClassificationName.COMMERCIAL_DOWNGRADE in selected:
            ineligible_reasons.append(RemunerationEligibilityReason.DOWNGRADE)
        if (
            OperationalDecisionName.TICKET_MISSING in selected
            or OperationalDecisionName.NON_PLAN_CHANGE_TICKET in selected
        ):
            ineligible_reasons.append(
                RemunerationEligibilityReason.NO_PLAN_CHANGE_TICKET
            )
        if OperationalDecisionName.NON_SUPPORT_TICKET in selected:
            ineligible_reasons.append(
                RemunerationEligibilityReason.TICKET_AUTHOR_NOT_SUPPORT
            )

        has_additional_sale = any(
            item.name == CommercialClassificationName.COMMON_ADDITIONAL_SALE
            for item in additional.selected
        )
        no_commercial_event = (
            CommercialClassificationName.RECURRING_REVENUE_UNCHANGED in selected
            and not has_additional_sale
        )
        if no_commercial_event:
            ineligible_reasons.append(RemunerationEligibilityReason.NO_COMMERCIAL_EVENT)
        if ineligible_reasons:
            return _result(
                RemunerationEligibilityStatus.NOT_ELIGIBLE,
                tuple(ineligible_reasons),
                commercial_ids,
                operational_ids,
            )

        return _result(
            RemunerationEligibilityStatus.POTENTIALLY_ELIGIBLE,
            (),
            commercial_ids,
            operational_ids,
        )

    @staticmethod
    def _additional_conclusions(
        available: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        return relevant_conclusions(
            available,
            frozenset(
                {
                    CommercialClassificationName.COMMON_ADDITIONAL_SALE,
                    CommercialClassificationName.COMMON_ADDITIONAL_CLASSIFICATION_NOT_EVALUABLE,
                    CommercialClassificationName.COMMON_ADDITIONAL_CLASSIFICATION_INCONSISTENT,
                }
            ),
        )

    def _resolve_additional_sale(
        self,
        available: tuple[EvaluationConclusion, ...],
    ) -> ResolvedConclusionGroup:
        relevant = self._additional_conclusions(available)
        supporting_ids = tuple(item.conclusion_id for item in relevant)
        inconsistent_name = (
            CommercialClassificationName.COMMON_ADDITIONAL_CLASSIFICATION_INCONSISTENT
        )
        not_evaluable_name = (
            CommercialClassificationName.COMMON_ADDITIONAL_CLASSIFICATION_NOT_EVALUABLE
        )
        if has_duplicate_names(relevant) or any(
            item.name == inconsistent_name
            or item.status is ConclusionStatus.INCONSISTENT
            for item in relevant
        ):
            return ResolvedConclusionGroup(
                ConclusionStatus.INCONSISTENT,
                supporting_ids=supporting_ids,
            )
        if any(
            item.name == not_evaluable_name
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
        return ResolvedConclusionGroup(
            ConclusionStatus.TRUE,
            selected=tuple(
                item
                for item in relevant
                if item.name == CommercialClassificationName.COMMON_ADDITIONAL_SALE
            ),
            supporting_ids=supporting_ids,
        )
