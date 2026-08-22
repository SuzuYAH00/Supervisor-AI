from dataclasses import dataclass
from datetime import date, datetime, time

from supervisor_ai.application.persistence import (
    DelayOccurrence,
    DelayReview,
    EmployeeOccurrenceReport,
)
from supervisor_ai.application.ports import UnitOfWork, UnitOfWorkFactory
from supervisor_ai.rules_engine.delays import DelayDecision, DelayOccurrenceType

PENDING_REVIEW = "pending_review"
VALID = DelayDecision.VALID.value
CORRECTED = DelayDecision.CORRECTED.value


@dataclass(frozen=True, slots=True)
class GetOperationalDelaysQuery:
    competence_month: date
    collaborator_id: str | None = None
    delay_type: str | None = None
    review_status: str | None = None

    def __post_init__(self) -> None:
        if self.competence_month.day != 1:
            raise ValueError("competence_month must be the first day of a month")
        if self.collaborator_id is not None and not self.collaborator_id.strip():
            raise ValueError("collaborator_id must not be blank")
        if self.delay_type not in {
            None,
            DelayOccurrenceType.ENTRY.value,
            DelayOccurrenceType.PAUSE_DURATION.value,
        }:
            raise ValueError("delay_type is invalid")
        if self.review_status not in {None, PENDING_REVIEW, VALID, CORRECTED}:
            raise ValueError("review_status is invalid")


@dataclass(frozen=True, slots=True)
class OperationalDelaySourceFact:
    source_fact_type: str
    source_fact_id: str
    source: str
    source_reference: str
    source_extract_reference: str
    source_sheet: str
    source_row: int
    queue: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: int
    pause_type: str | None = None


@dataclass(frozen=True, slots=True)
class OperationalDelaySchedule:
    planned_start: time
    planned_end: time | None
    effective_origin: str
    source_reference: str | None
    source_sheet: str | None
    source_cell: str | None


@dataclass(frozen=True, slots=True)
class OperationalDelayItem:
    occurrence: DelayOccurrence
    display_name: str
    review_status: str
    counts_for_rv: bool
    current_review: DelayReview | None
    possible_reports: tuple[EmployeeOccurrenceReport, ...]
    source_fact: OperationalDelaySourceFact
    schedule: OperationalDelaySchedule | None


@dataclass(frozen=True, slots=True)
class GetOperationalDelaysResult:
    competence_month: date
    collaborator_id: str | None
    delay_type: str | None
    review_status: str | None
    detected_count: int
    pending_count: int
    valid_count: int
    corrected_count: int
    items: tuple[OperationalDelayItem, ...]


class GetOperationalDelaysUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._factory = unit_of_work_factory

    def execute(self, query: GetOperationalDelaysQuery) -> GetOperationalDelaysResult:
        with self._factory() as uow:
            collaborator_ids = (
                (query.collaborator_id,)
                if query.collaborator_id is not None
                else tuple(
                    profile.collaborator_id
                    for profile in uow.operational_collaborators.list_all()
                )
            )
            occurrences = tuple(
                occurrence
                for collaborator_id in collaborator_ids
                for occurrence in uow.delay_occurrences.search_month(
                    collaborator_id=collaborator_id,
                    competence_month=query.competence_month,
                )
                if query.delay_type is None
                or occurrence.occurrence_type == query.delay_type
            )
            reviews = uow.delay_reviews.get_latest_for_occurrences(
                tuple(item.id for item in occurrences)
            )
            review_by_occurrence = {
                review.delay_occurrence_id: review for review in reviews
            }
            items = tuple(
                _project_item(uow, occurrence, review_by_occurrence.get(occurrence.id))
                for occurrence in occurrences
            )
        filtered = tuple(
            item
            for item in items
            if query.review_status is None or item.review_status == query.review_status
        )
        return GetOperationalDelaysResult(
            query.competence_month,
            query.collaborator_id,
            query.delay_type,
            query.review_status,
            len(items),
            sum(item.review_status == PENDING_REVIEW for item in items),
            sum(item.review_status == VALID for item in items),
            sum(item.review_status == CORRECTED for item in items),
            filtered,
        )


def _project_item(
    uow: UnitOfWork,
    occurrence: DelayOccurrence,
    review: DelayReview | None,
) -> OperationalDelayItem:
    status = PENDING_REVIEW if review is None else review.decision
    reports = uow.employee_occurrence_reports.search_by_collaborator_date(
        collaborator_id=occurrence.collaborator_id,
        occurrence_date=occurrence.occurrence_date,
    )
    if occurrence.source_fact_type == "work_session":
        fact = uow.work_sessions.get_by_id(occurrence.source_fact_id)
        schedule_fact = uow.daily_planned_work_schedules.get_by_collaborator_date(
            collaborator_id=occurrence.collaborator_id,
            work_date=occurrence.occurrence_date,
        )
        override = uow.daily_work_schedule_overrides.get_for_date(
            collaborator_id=occurrence.collaborator_id,
            work_date=occurrence.occurrence_date,
        )
        if schedule_fact is None and override is None:
            raise RuntimeError("delay planned schedule was not found")
        schedule = OperationalDelaySchedule(
            override.planned_start if override else schedule_fact.planned_start,  # type: ignore[union-attr]
            override.planned_end if override else schedule_fact.planned_end,  # type: ignore[union-attr]
            "override" if override else schedule_fact.source_type,  # type: ignore[union-attr]
            None if override else schedule_fact.source_reference,  # type: ignore[union-attr]
            None if override else schedule_fact.source_sheet,  # type: ignore[union-attr]
            None if override else schedule_fact.source_cell,  # type: ignore[union-attr]
        )
    else:
        fact = uow.pauses.get_by_id(occurrence.source_fact_id)
        schedule = None
    if fact is None:
        raise RuntimeError("delay source fact was not found")
    source_fact = OperationalDelaySourceFact(
        occurrence.source_fact_type,
        occurrence.source_fact_id,
        fact.source,
        fact.external_reference,
        fact.source_extract_reference,
        fact.source_sheet,
        fact.source_row,
        fact.queue,
        fact.started_at,
        fact.ended_at,
        fact.duration_seconds,
        getattr(fact, "pause_type", None),
    )
    return OperationalDelayItem(
        occurrence,
        occurrence.collaborator_id,
        status,
        status != CORRECTED,
        review,
        reports,
        source_fact,
        schedule,
    )
