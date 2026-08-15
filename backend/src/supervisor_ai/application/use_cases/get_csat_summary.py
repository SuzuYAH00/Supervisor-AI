from dataclasses import dataclass
from decimal import Decimal

from supervisor_ai.application.csat import CsatFilters
from supervisor_ai.application.persistence import CsatSummaryGroupRecord
from supervisor_ai.application.ports import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class CsatSummaryGroup:
    value: str | None
    evaluation_count: int
    score_average: Decimal


@dataclass(frozen=True, slots=True)
class GetCsatSummaryResult:
    filters: CsatFilters
    evaluation_count: int
    score_average: Decimal | None
    by_collaborator: tuple[CsatSummaryGroup, ...]
    by_channel: tuple[CsatSummaryGroup, ...]


class GetCsatSummaryUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: CsatFilters) -> GetCsatSummaryResult:
        with self._unit_of_work_factory() as unit_of_work:
            record = unit_of_work.csat.summarize(
                collaborator_id=query.collaborator_id,
                start_date=query.start_date,
                end_date=query.end_date,
                source=query.source,
                channel=query.channel,
            )
        return GetCsatSummaryResult(
            filters=query,
            evaluation_count=record.evaluation_count,
            score_average=_average(record.score_total, record.evaluation_count),
            by_collaborator=_groups(record.by_collaborator),
            by_channel=_groups(record.by_channel),
        )


def _groups(
    records: tuple[CsatSummaryGroupRecord, ...],
) -> tuple[CsatSummaryGroup, ...]:
    return tuple(
        CsatSummaryGroup(
            value=item.value,
            evaluation_count=item.evaluation_count,
            score_average=item.score_total / Decimal(item.evaluation_count),
        )
        for item in records
    )


def _average(total: Decimal, count: int) -> Decimal | None:
    return None if count == 0 else total / Decimal(count)
