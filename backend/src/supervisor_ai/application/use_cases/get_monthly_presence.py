from dataclasses import dataclass
from datetime import date

from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.rules_engine import PresenceDay, summarize_monthly_presence


@dataclass(frozen=True, slots=True)
class GetMonthlyPresenceQuery:
    collaborator_id: str
    competence_month: date

    def __post_init__(self) -> None:
        if not self.collaborator_id.strip():
            raise ValueError("collaborator_id must not be blank")
        if self.competence_month.day != 1:
            raise ValueError("competence_month must be the first day of a month")


@dataclass(frozen=True, slots=True)
class GetMonthlyPresenceResult:
    collaborator_id: str
    competence_month: date
    worked_days: int
    penalizable_absence_days: int
    non_penalizable_absence_days: int
    meets_minimum_worked_days: bool


class GetMonthlyPresenceUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: GetMonthlyPresenceQuery) -> GetMonthlyPresenceResult:
        with self._unit_of_work_factory() as unit_of_work:
            facts = unit_of_work.daily_work_statuses.search_month(
                collaborator_id=query.collaborator_id,
                competence_month=query.competence_month,
            )
        summary = summarize_monthly_presence(
            tuple(PresenceDay(item.work_date, item.raw_code) for item in facts)
        )
        return GetMonthlyPresenceResult(
            collaborator_id=query.collaborator_id,
            competence_month=query.competence_month,
            worked_days=summary.worked_days,
            penalizable_absence_days=summary.penalizable_absence_days,
            non_penalizable_absence_days=summary.non_penalizable_absence_days,
            meets_minimum_worked_days=summary.meets_minimum_worked_days,
        )
