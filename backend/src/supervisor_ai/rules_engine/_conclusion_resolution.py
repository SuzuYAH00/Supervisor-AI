from dataclasses import dataclass

from supervisor_ai.rules_engine.types import ConclusionStatus, EvaluationConclusion


@dataclass(frozen=True, slots=True)
class ResolvedConclusionGroup:
    """Resultado interno da resolução determinística de um grupo exclusivo."""

    status: ConclusionStatus
    selected: tuple[EvaluationConclusion, ...] = ()
    supporting_ids: tuple[str, ...] = ()


def relevant_conclusions(
    available: tuple[EvaluationConclusion, ...],
    names: frozenset[str],
) -> tuple[EvaluationConclusion, ...]:
    """Localiza conclusões sem depender da ordem recebida."""

    return tuple(
        sorted(
            (item for item in available if item.name in names),
            key=lambda item: (item.name, item.conclusion_id),
        )
    )


def has_duplicate_names(conclusions: tuple[EvaluationConclusion, ...]) -> bool:
    """Indica ambiguidade quando um mesmo nome aparece mais de uma vez."""

    names = tuple(item.name for item in conclusions)
    return len(names) != len(set(names))


def resolve_exclusive_conclusion_group(
    available: tuple[EvaluationConclusion, ...],
    *,
    positive_names: frozenset[str],
    not_evaluable_name: str,
    inconsistent_name: str,
) -> ResolvedConclusionGroup:
    """Resolve um grupo com exatamente uma conclusão positiva esperada."""

    all_names = positive_names | {not_evaluable_name, inconsistent_name}
    relevant = relevant_conclusions(available, all_names)
    supporting_ids = tuple(item.conclusion_id for item in relevant)

    if has_duplicate_names(relevant):
        return ResolvedConclusionGroup(
            ConclusionStatus.INCONSISTENT,
            supporting_ids=supporting_ids,
        )
    if any(
        item.name == inconsistent_name or item.status is ConclusionStatus.INCONSISTENT
        for item in relevant
    ):
        return ResolvedConclusionGroup(
            ConclusionStatus.INCONSISTENT,
            supporting_ids=supporting_ids,
        )
    if any(
        item.name == not_evaluable_name or item.status is ConclusionStatus.NOT_EVALUABLE
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
    if len(selected) > 1:
        return ResolvedConclusionGroup(
            ConclusionStatus.INCONSISTENT,
            supporting_ids=supporting_ids,
        )
    return ResolvedConclusionGroup(
        ConclusionStatus.TRUE,
        selected=selected,
        supporting_ids=supporting_ids,
    )
