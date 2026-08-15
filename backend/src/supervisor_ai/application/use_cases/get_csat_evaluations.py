from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from supervisor_ai.application.csat import CsatFilters
from supervisor_ai.application.ports import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class CsatEvaluationItem:
    evaluation_id: str
    external_reference: str
    source: str
    collaborator_id: str
    channel: str | None
    score: Decimal
    evaluated_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class GetCsatEvaluationsResult:
    filters: CsatFilters
    evaluation_count: int
    items: tuple[CsatEvaluationItem, ...]


class GetCsatEvaluationsUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: CsatFilters) -> GetCsatEvaluationsResult:
        with self._unit_of_work_factory() as unit_of_work:
            evaluations = unit_of_work.csat.search(
                collaborator_id=query.collaborator_id,
                start_date=query.start_date,
                end_date=query.end_date,
                source=query.source,
                channel=query.channel,
            )
        items = tuple(
            CsatEvaluationItem(
                evaluation_id=item.id,
                external_reference=item.external_reference,
                source=item.source,
                collaborator_id=item.collaborator_id,
                channel=item.channel,
                score=item.score,
                evaluated_at=item.evaluated_at,
                created_at=item.created_at,
            )
            for item in evaluations
        )
        return GetCsatEvaluationsResult(query, len(items), items)
