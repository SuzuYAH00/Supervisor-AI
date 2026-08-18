from dataclasses import dataclass, replace
from datetime import date, datetime, time
from hashlib import sha256

from supervisor_ai.application.errors import WorkScheduleConflict
from supervisor_ai.application.persistence import (
    CollaboratorWorkSchedule,
    DailyPlannedWorkScheduleFact,
    DailyWorkScheduleOverride,
    IngestionCoverageEvidence,
)
from supervisor_ai.application.ports import Clock, UnitOfWorkFactory

PLANNED_WORK_SCHEDULES_DATASET = "planned_work_schedules"
ATTENDANCE_SHEET_SOURCE = "attendance_sheet"


@dataclass(frozen=True, slots=True)
class CollaboratorWorkScheduleInput:
    external_identity: str
    standard_start: time
    standard_end: time
    effective_from: date
    effective_until: date | None
    source: str
    source_reference: str


@dataclass(frozen=True, slots=True)
class DailyPlannedWorkScheduleInput:
    external_identity: str
    work_date: date
    planned_start: time | None
    planned_end: time | None
    source_type: str
    source: str
    source_reference: str
    source_sheet: str
    source_cell: str
    unresolved_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ImportWorkSchedulesCommand:
    standards: tuple[CollaboratorWorkScheduleInput, ...] = ()
    daily_schedules: tuple[DailyPlannedWorkScheduleInput, ...] = ()
    covered_through: date | None = None
    import_reference: str | None = None


@dataclass(frozen=True, slots=True)
class ImportWorkSchedulesResult:
    created_standards: int
    created_daily_schedules: int
    idempotent_items: int


class ImportWorkSchedulesUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._factory = unit_of_work_factory
        self._clock = clock

    def execute(self, command: ImportWorkSchedulesCommand) -> ImportWorkSchedulesResult:
        now = self._clock()
        standards = daily = same = 0
        with self._factory() as uow:
            for item in command.standards:
                fact = _standard(item, _resolve(uow, item.external_identity), now)
                existing = uow.collaborator_work_schedules.get_by_id(fact.id)
                overlaps = uow.collaborator_work_schedules.find_overlapping(
                    collaborator_id=fact.collaborator_id,
                    effective_from=fact.effective_from,
                    effective_until=fact.effective_until,
                )
                if existing is not None:
                    if _without_created(existing) != _without_created(fact):
                        raise WorkScheduleConflict("standard schedule identity differs")
                    same += 1
                elif overlaps:
                    raise WorkScheduleConflict("standard schedule periods overlap")
                else:
                    uow.collaborator_work_schedules.add(fact)
                    standards += 1
            for item in command.daily_schedules:
                collaborator_id = _resolve(uow, item.external_identity)
                if item.unresolved_reason == "standard_schedule_not_found":
                    standard = uow.collaborator_work_schedules.find_for_date(
                        collaborator_id=collaborator_id, work_date=item.work_date
                    )
                    if standard is not None:
                        item = replace(
                            item,
                            planned_start=standard.standard_start,
                            planned_end=standard.standard_end,
                            source_type="standard",
                            unresolved_reason=None,
                        )
                fact = _daily(item, collaborator_id, now)
                existing = uow.daily_planned_work_schedules.get_by_collaborator_date(
                    collaborator_id=fact.collaborator_id, work_date=fact.work_date
                )
                if existing is None:
                    uow.daily_planned_work_schedules.add(fact)
                    daily += 1
                elif _without_created(existing) == _without_created(fact):
                    same += 1
                elif (
                    existing.source_type == "explicit"
                    and fact.source_type != "explicit"
                ):
                    same += 1
                else:
                    raise WorkScheduleConflict("daily planned schedule differs")
            if command.covered_through is not None:
                if not command.import_reference:
                    raise ValueError("import_reference is required for coverage")
                evidence = IngestionCoverageEvidence(
                    PLANNED_WORK_SCHEDULES_DATASET,
                    ATTENDANCE_SHEET_SOURCE,
                    command.import_reference,
                    command.covered_through,
                    now,
                )
                existing = uow.ingestion_coverages.get_by_import_reference(
                    dataset=evidence.dataset,
                    source=evidence.source,
                    import_reference=evidence.import_reference,
                )
                if existing is None:
                    uow.ingestion_coverages.add(evidence)
                elif existing.covered_through != evidence.covered_through:
                    raise WorkScheduleConflict("schedule coverage reference differs")
            uow.commit()
        return ImportWorkSchedulesResult(standards, daily, same)


@dataclass(frozen=True, slots=True)
class RecordDailyWorkScheduleOverrideCommand:
    override_id: str
    collaborator_id: str
    work_date: date
    planned_start: time
    planned_end: time
    reason: str
    created_by: str


class RecordDailyWorkScheduleOverrideUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._factory = unit_of_work_factory
        self._clock = clock

    def execute(
        self, command: RecordDailyWorkScheduleOverrideCommand
    ) -> DailyWorkScheduleOverride:
        override = DailyWorkScheduleOverride(
            command.override_id,
            command.collaborator_id,
            command.work_date,
            command.planned_start,
            command.planned_end,
            command.reason,
            command.created_by,
            self._clock(),
        )
        with self._factory() as uow:
            existing = uow.daily_work_schedule_overrides.get_for_date(
                collaborator_id=command.collaborator_id, work_date=command.work_date
            )
            if existing is None:
                uow.daily_work_schedule_overrides.add(override)
            elif existing != override:
                raise WorkScheduleConflict("daily schedule override already exists")
            uow.commit()
        return override


def _standard(
    item: CollaboratorWorkScheduleInput, collaborator_id: str, now: datetime
) -> CollaboratorWorkSchedule:
    digest = sha256(f"{item.source}\0{item.source_reference}".encode()).hexdigest()
    return CollaboratorWorkSchedule(
        f"work-schedule-{digest}",
        collaborator_id,
        item.standard_start,
        item.standard_end,
        item.effective_from,
        item.effective_until,
        item.source,
        item.source_reference,
        now,
    )


def _daily(
    item: DailyPlannedWorkScheduleInput, collaborator_id: str, now: datetime
) -> DailyPlannedWorkScheduleFact:
    digest = sha256(f"{item.source}\0{item.source_reference}".encode()).hexdigest()
    return DailyPlannedWorkScheduleFact(
        f"daily-schedule-{digest}",
        collaborator_id,
        item.work_date,
        item.planned_start,
        item.planned_end,
        item.source_type,
        item.source,
        item.source_reference,
        item.source_sheet,
        item.source_cell,
        item.unresolved_reason,
        now,
    )


def _without_created(item: object) -> tuple[object, ...]:
    return tuple(
        getattr(item, name)
        for name in item.__dataclass_fields__
        if name != "created_at"
    )


def _resolve(uow: object, external_identity: str) -> str:
    identity = uow.collaborator_external_identities.get_by_source_identity(
        source=ATTENDANCE_SHEET_SOURCE, external_identity=external_identity
    )
    if identity is None:
        from supervisor_ai.application.errors import (
            CollaboratorExternalIdentityNotFound,
        )

        raise CollaboratorExternalIdentityNotFound(external_identity)
    return identity.collaborator_id
