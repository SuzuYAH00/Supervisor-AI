from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from supervisor_ai.application.recurrence import RECURRENCE_COMPETITIVE_SOURCE
from supervisor_ai.application.use_cases.get_recurrence_summary_from_coverage import (
    GetRecurrenceSummaryFromCoverageQuery,
    GetRecurrenceSummaryFromCoverageUseCase,
)


@dataclass(frozen=True, slots=True)
class GetMonthlyRecurrenceFactsQuery:
    cohort_month: date
    collaborator_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.cohort_month.day != 1:
            raise ValueError("cohort_month must be the first day of a month")
        if len(self.collaborator_ids) != len(set(self.collaborator_ids)):
            raise ValueError("collaborator_ids must not contain duplicates")
        if any(not value.strip() for value in self.collaborator_ids):
            raise ValueError("collaborator_ids must not contain blank values")


@dataclass(frozen=True, slots=True)
class MonthlyRecurrenceFact:
    collaborator_id: str
    cohort_month: date
    eligible_attendance_count: int
    recurrence_count: int
    recurrence_rate: Decimal | None


@dataclass(frozen=True, slots=True)
class GetMonthlyRecurrenceFactsResult:
    cohort_month: date
    items: tuple[MonthlyRecurrenceFact, ...]


class GetMonthlyRecurrenceFactsUseCase:
    """Projeta o resumo coberto do MK sem recalcular Reincidência."""

    def __init__(
        self, summary: GetRecurrenceSummaryFromCoverageUseCase
    ) -> None:
        self._summary = summary

    def execute(
        self, query: GetMonthlyRecurrenceFactsQuery
    ) -> GetMonthlyRecurrenceFactsResult:
        summary = self._summary.execute(
            GetRecurrenceSummaryFromCoverageQuery(
                reference_month=query.cohort_month,
                source=RECURRENCE_COMPETITIVE_SOURCE,
            )
        )
        by_operator = {item.operator_id: item for item in summary.by_operator}
        return GetMonthlyRecurrenceFactsResult(
            cohort_month=query.cohort_month,
            items=tuple(
                MonthlyRecurrenceFact(
                    collaborator_id=collaborator_id,
                    cohort_month=query.cohort_month,
                    eligible_attendance_count=(
                        by_operator[collaborator_id].eligible_attendance_count
                        if collaborator_id in by_operator
                        else 0
                    ),
                    recurrence_count=(
                        by_operator[collaborator_id].recurrence_count
                        if collaborator_id in by_operator
                        else 0
                    ),
                    recurrence_rate=(
                        by_operator[collaborator_id].recurrence_rate
                        if collaborator_id in by_operator
                        else None
                    ),
                )
                for collaborator_id in query.collaborator_ids
            ),
        )
