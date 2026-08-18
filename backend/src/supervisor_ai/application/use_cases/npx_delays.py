from dataclasses import dataclass
from datetime import date, datetime, time
from hashlib import sha256
from zoneinfo import ZoneInfo

from supervisor_ai.application.errors import (
    DelayOccurrenceNotFound,
    DelayReviewConflict,
    IngestionCoverageConflict,
    NpxFactConflict,
    WorkScheduleIncomplete,
)
from supervisor_ai.application.persistence import (
    DelayOccurrence,
    DelayReview,
    IngestionCoverageEvidence,
    PauseFact,
    WorkSessionFact,
)
from supervisor_ai.application.ports import Clock, UnitOfWork, UnitOfWorkFactory
from supervisor_ai.application.use_cases.work_schedules import (
    ATTENDANCE_SHEET_SOURCE,
    PLANNED_WORK_SCHEDULES_DATASET,
)
from supervisor_ai.rules_engine.delays import (
    DelayDecision,
    DelayOccurrenceType,
    evaluate_entry_delay,
    evaluate_pause_delay,
    month_bounds,
)

NPX_SOURCE = "npx"
NPX_WORK_SESSIONS_DATASET = "npx_work_sessions"
NPX_PAUSES_DATASET = "npx_pauses"
WORKED_DAY_CODES = frozenset({"P", "PS", "PD", "PF", "FT", "PL", "EX"})


@dataclass(frozen=True, slots=True)
class NpxCoverageDeclaration:
    covered_through: date
    import_reference: str


@dataclass(frozen=True, slots=True)
class WorkSessionInput:
    fact_id: str
    external_reference: str
    external_identity: str
    external_agent_id: str | None
    queue: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: int
    source_extract_reference: str
    source_sheet: str
    source_row: int


@dataclass(frozen=True, slots=True)
class PauseInput(WorkSessionInput):
    pause_type: str
    supervisor_released: str | None = None


@dataclass(frozen=True, slots=True)
class NpxImportIssue:
    source_row: int
    external_identity: str
    code: str
    invalid_value: str | None = None


@dataclass(frozen=True, slots=True)
class ImportNpxFactsCommand:
    work_sessions: tuple[WorkSessionInput, ...] = ()
    pauses: tuple[PauseInput, ...] = ()
    work_session_coverage: NpxCoverageDeclaration | None = None
    pause_coverage: NpxCoverageDeclaration | None = None


@dataclass(frozen=True, slots=True)
class ImportNpxFactsResult:
    imported_work_sessions: int
    imported_pauses: int
    idempotent_rows: int
    conflict_rows: int
    rejected_rows: int
    delay_occurrences_created: int
    issues: tuple[NpxImportIssue, ...]


class ImportNpxFactsUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(self, command: ImportNpxFactsCommand) -> ImportNpxFactsResult:
        now = self._clock()
        _require_aware(now)
        sessions = pauses = idempotent = conflicts = rejected = derived = 0
        issues: list[NpxImportIssue] = []
        with self._unit_of_work_factory() as uow:
            for item in command.work_sessions:
                collaborator_id = _resolve(uow, item, issues)
                if collaborator_id is None:
                    rejected += 1
                    continue
                fact = _work_session_fact(item, collaborator_id, now)
                state = _store_fact(uow.work_sessions, fact)
                sessions += state == "created"
                idempotent += state == "same"
                conflicts += state == "conflict"
                if state == "conflict":
                    issues.append(
                        NpxImportIssue(
                            item.source_row,
                            item.external_identity,
                            "conflicting_work_session",
                            item.external_reference,
                        )
                    )
            for item in command.pauses:
                collaborator_id = _resolve(uow, item, issues)
                if collaborator_id is None:
                    rejected += 1
                    continue
                fact = _pause_fact(item, collaborator_id, now)
                state = _store_fact(uow.pauses, fact)
                pauses += state == "created"
                idempotent += state == "same"
                conflicts += state == "conflict"
                if state == "conflict":
                    issues.append(
                        NpxImportIssue(
                            item.source_row,
                            item.external_identity,
                            "conflicting_pause",
                            item.external_reference,
                        )
                    )
                    continue
                evaluation = evaluate_pause_delay(
                    pause_type=fact.pause_type, duration_seconds=fact.duration_seconds
                )
                if evaluation.is_delay and evaluation.applied_limit_seconds is not None:
                    occurrence = _pause_occurrence(
                        fact, evaluation.applied_limit_seconds, now
                    )
                    existing = uow.delay_occurrences.get_by_source_fact(
                        source_fact_type="pause", source_fact_id=fact.id
                    )
                    if existing is None:
                        uow.delay_occurrences.add(occurrence)
                        derived += 1
                    elif _without_created_at(existing) != _without_created_at(
                        occurrence
                    ):
                        raise NpxFactConflict(
                            "derived pause delay differs from persisted facts"
                        )
            _coverage(
                uow, NPX_WORK_SESSIONS_DATASET, command.work_session_coverage, now
            )
            _coverage(uow, NPX_PAUSES_DATASET, command.pause_coverage, now)
            uow.commit()
        return ImportNpxFactsResult(
            sessions, pauses, idempotent, conflicts, rejected, derived, tuple(issues)
        )


@dataclass(frozen=True, slots=True)
class RecordDelayReviewCommand:
    review_id: str
    delay_occurrence_id: str
    decision: DelayDecision
    decided_at: datetime
    decided_by: str
    employee_occurrence_report_id: str | None = None
    note: str | None = None


class RecordDelayReviewUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(self, command: RecordDelayReviewCommand) -> DelayReview:
        now = self._clock()
        _require_aware(now)
        with self._unit_of_work_factory() as uow:
            occurrence = uow.delay_occurrences.get_by_id(command.delay_occurrence_id)
            if occurrence is None:
                raise DelayOccurrenceNotFound(command.delay_occurrence_id)
            if command.employee_occurrence_report_id is not None:
                report = uow.employee_occurrence_reports.get_by_id(
                    command.employee_occurrence_report_id
                )
                if (
                    report is None
                    or report.collaborator_id != occurrence.collaborator_id
                    or report.occurrence_date != occurrence.occurrence_date
                ):
                    raise DelayReviewConflict(
                        "employee occurrence report does not match "
                        "delay collaborator and date"
                    )
            review = DelayReview(
                command.review_id,
                command.delay_occurrence_id,
                command.decision.value,
                command.decided_at,
                command.decided_by,
                command.employee_occurrence_report_id,
                command.note,
                now,
            )
            existing = uow.delay_reviews.get_by_id(review.id)
            if existing is None:
                uow.delay_reviews.add(review)
            elif existing != review:
                raise DelayReviewConflict(
                    "review identity differs from persisted decision"
                )
            uow.commit()
            return review


@dataclass(frozen=True, slots=True)
class GetMonthlyDelayCountQuery:
    collaborator_id: str
    competence_month: date


@dataclass(frozen=True, slots=True)
class MonthlyDelayCountResult:
    collaborator_id: str
    competence_month: date
    delay_count: int


class GetMonthlyDelayCountUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: GetMonthlyDelayCountQuery) -> MonthlyDelayCountResult:
        with self._unit_of_work_factory() as uow:
            occurrences = uow.delay_occurrences.search_month(
                collaborator_id=query.collaborator_id,
                competence_month=query.competence_month,
            )
            reviews = uow.delay_reviews.get_latest_for_occurrences(
                tuple(item.id for item in occurrences)
            )
        decisions = {item.delay_occurrence_id: item.decision for item in reviews}
        count = sum(
            decisions.get(item.id) != DelayDecision.CORRECTED.value
            for item in occurrences
        )
        return MonthlyDelayCountResult(
            query.collaborator_id, query.competence_month, count
        )


@dataclass(frozen=True, slots=True)
class GetMonthlyDelayFactsQuery:
    competence_month: date
    collaborator_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GetMonthlyDelayFactsResult:
    competence_month: date
    items: tuple[MonthlyDelayCountResult, ...]


class GetMonthlyDelayFactsFromCoverageUseCase:
    """Fecha atrasos somente com sessões, pausas e jornadas comprovadamente cobertas."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._factory = unit_of_work_factory
        self._clock = clock

    def execute(self, query: GetMonthlyDelayFactsQuery) -> GetMonthlyDelayFactsResult:
        _, required_through = month_bounds(query.competence_month)
        now = self._clock()
        with self._factory() as uow:
            for dataset, source in (
                (NPX_WORK_SESSIONS_DATASET, NPX_SOURCE),
                (NPX_PAUSES_DATASET, NPX_SOURCE),
                (PLANNED_WORK_SCHEDULES_DATASET, ATTENDANCE_SHEET_SOURCE),
            ):
                evidence = uow.ingestion_coverages.get_latest(
                    dataset=dataset, source=source
                )
                if evidence is None or evidence.covered_through < required_through:
                    raise WorkScheduleIncomplete(
                        "coverage is incomplete for "
                        f"{dataset} through {required_through}"
                    )
            statuses = uow.daily_work_statuses.search_competence(
                competence_month=query.competence_month,
                collaborator_ids=query.collaborator_ids,
            )
            schedules = {
                (item.collaborator_id, item.work_date): item
                for item in uow.daily_planned_work_schedules.search_competence(
                    competence_month=query.competence_month,
                    collaborator_ids=query.collaborator_ids,
                )
            }
            for status in statuses:
                if status.raw_code not in WORKED_DAY_CODES or status.raw_code == "PL":
                    continue
                override = uow.daily_work_schedule_overrides.get_for_date(
                    collaborator_id=status.collaborator_id, work_date=status.work_date
                )
                schedule = schedules.get((status.collaborator_id, status.work_date))
                planned_start = (
                    override.planned_start
                    if override
                    else (None if schedule is None else schedule.planned_start)
                )
                if planned_start is None:
                    raise WorkScheduleIncomplete(
                        "planned schedule unresolved for "
                        f"{status.collaborator_id} on {status.work_date}"
                    )
                sessions = uow.work_sessions.search_date(
                    collaborator_id=status.collaborator_id, work_date=status.work_date
                )
                if not sessions:
                    continue
                first = sessions[0]
                observed = (
                    first.started_at.astimezone(ZoneInfo("America/Fortaleza"))
                    .time()
                    .replace(tzinfo=None)
                )
                if evaluate_entry_delay(
                    planned_start=planned_start, observed_start=observed
                ):
                    occurrence = _entry_occurrence(first, planned_start, observed, now)
                    existing = uow.delay_occurrences.get_by_source_fact(
                        source_fact_type="work_session", source_fact_id=first.id
                    )
                    if existing is None:
                        uow.delay_occurrences.add(occurrence)
                    elif _without_created_at(existing) != _without_created_at(
                        occurrence
                    ):
                        raise NpxFactConflict(
                            "derived entry delay differs from persisted facts"
                        )
            uow.commit()
        counter = GetMonthlyDelayCountUseCase(self._factory)
        return GetMonthlyDelayFactsResult(
            query.competence_month,
            tuple(
                counter.execute(GetMonthlyDelayCountQuery(item, query.competence_month))
                for item in query.collaborator_ids
            ),
        )


def _resolve(
    uow: UnitOfWork, item: WorkSessionInput, issues: list[NpxImportIssue]
) -> str | None:
    identity = uow.collaborator_external_identities.get_by_source_identity(
        source=NPX_SOURCE, external_identity=item.external_identity
    )
    if identity is None:
        issues.append(
            NpxImportIssue(
                item.source_row,
                item.external_identity,
                "unknown_collaborator_alias",
                item.external_identity,
            )
        )
        return None
    return identity.collaborator_id


def _store_fact(repository: object, fact: WorkSessionFact | PauseFact) -> str:
    existing = repository.get_by_source_reference(
        source=fact.source, external_reference=fact.external_reference
    ) or repository.get_by_id(fact.id)  # type: ignore[attr-defined]
    if existing is None:
        repository.add(fact)
        return "created"  # type: ignore[attr-defined]
    return (
        "same"
        if _without_created_at(existing) == _without_created_at(fact)
        else "conflict"
    )


def _work_session_fact(
    item: WorkSessionInput, collaborator_id: str, now: datetime
) -> WorkSessionFact:
    return WorkSessionFact(
        item.fact_id,
        item.external_reference,
        NPX_SOURCE,
        collaborator_id,
        item.external_identity,
        item.external_agent_id,
        item.queue,
        item.started_at,
        item.ended_at,
        item.duration_seconds,
        item.source_extract_reference,
        item.source_sheet,
        item.source_row,
        now,
    )


def _pause_fact(item: PauseInput, collaborator_id: str, now: datetime) -> PauseFact:
    return PauseFact(
        item.fact_id,
        item.external_reference,
        NPX_SOURCE,
        collaborator_id,
        item.external_identity,
        item.external_agent_id,
        item.queue,
        item.pause_type,
        item.started_at,
        item.ended_at,
        item.duration_seconds,
        item.supervisor_released,
        item.source_extract_reference,
        item.source_sheet,
        item.source_row,
        now,
    )


def _without_created_at(
    item: WorkSessionFact | PauseFact | DelayOccurrence,
) -> tuple[object, ...]:
    return tuple(
        getattr(item, name)
        for name in item.__dataclass_fields__
        if name != "created_at"
    )


def _coverage(
    uow: UnitOfWork,
    dataset: str,
    declaration: NpxCoverageDeclaration | None,
    now: datetime,
) -> None:
    if declaration is None:
        return
    evidence = IngestionCoverageEvidence(
        dataset,
        NPX_SOURCE,
        declaration.import_reference,
        declaration.covered_through,
        now,
    )
    existing = uow.ingestion_coverages.get_by_import_reference(
        dataset=dataset,
        source=NPX_SOURCE,
        import_reference=declaration.import_reference,
    )
    if existing is None:
        uow.ingestion_coverages.add(evidence)
    elif existing.covered_through != evidence.covered_through:
        raise IngestionCoverageConflict(
            "coverage reference differs from persisted evidence"
        )


def _pause_occurrence(fact: PauseFact, limit: int, now: datetime) -> DelayOccurrence:
    digest = sha256(f"pause\0{fact.id}".encode()).hexdigest()
    return DelayOccurrence(
        f"delay-{digest}",
        fact.collaborator_id,
        fact.started_at.date(),
        DelayOccurrenceType.PAUSE_DURATION.value,
        "pause",
        fact.id,
        fact.duration_seconds,
        limit,
        now,
    )


def _entry_occurrence(
    fact: WorkSessionFact, planned_start: time, observed_start: time, now: datetime
) -> DelayOccurrence:
    digest = sha256(f"work_session\0{fact.id}".encode()).hexdigest()
    planned_seconds = planned_start.hour * 3600 + planned_start.minute * 60
    observed_seconds = (
        observed_start.hour * 3600 + observed_start.minute * 60 + observed_start.second
    )
    return DelayOccurrence(
        f"delay-{digest}",
        fact.collaborator_id,
        fact.started_at.astimezone(ZoneInfo("America/Fortaleza")).date(),
        DelayOccurrenceType.ENTRY.value,
        "work_session",
        fact.id,
        observed_seconds,
        planned_seconds + 59,
        now,
    )


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
