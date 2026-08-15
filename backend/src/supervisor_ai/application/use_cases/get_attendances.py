from dataclasses import dataclass
from datetime import datetime

from supervisor_ai.application.persistence import AttendanceFact
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.application.recurrence import AttendanceFilters
from supervisor_ai.rules_engine import ClassificationIdentity


@dataclass(frozen=True, slots=True)
class AttendanceItem:
    attendance_id: str
    external_reference: str
    source: str
    customer_code: str
    operator_id: str
    channel: str
    occurred_at: datetime
    process: ClassificationIdentity
    opening_classification: ClassificationIdentity
    closing_classification: ClassificationIdentity
    created_at: datetime


@dataclass(frozen=True, slots=True)
class GetAttendancesResult:
    filters: AttendanceFilters
    items: tuple[AttendanceItem, ...]


class GetAttendancesUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: AttendanceFilters) -> GetAttendancesResult:
        with self._unit_of_work_factory() as unit_of_work:
            facts = unit_of_work.attendances.search(
                operator_id=query.operator_id,
                customer_code=query.customer_code,
                source=query.source,
                channel=query.channel,
                start_date=query.start_date,
                end_date=query.end_date,
            )
        return GetAttendancesResult(
            filters=query, items=tuple(_item(fact) for fact in facts)
        )


def _item(fact: AttendanceFact) -> AttendanceItem:
    return AttendanceItem(
        attendance_id=fact.id,
        external_reference=fact.external_reference,
        source=fact.source,
        customer_code=fact.customer_code,
        operator_id=fact.operator_id,
        channel=fact.channel,
        occurred_at=fact.occurred_at,
        process=fact.process,
        opening_classification=fact.opening_classification,
        closing_classification=fact.closing_classification,
        created_at=fact.created_at,
    )
