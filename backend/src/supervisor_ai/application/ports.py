from datetime import date, datetime
from types import TracebackType
from typing import Protocol, Self

from supervisor_ai.application.mk_operational import (
    MkAttendanceMirror,
    MkBotConversationMirror,
    MkSyncRun,
    MkSyncState,
    MkUpsertOutcome,
)
from supervisor_ai.application.persistence import (
    AttendanceFact,
    CollaboratorExternalIdentity,
    CollaboratorFinancialTimelineCursorPosition,
    CollaboratorFinancialTimelineRecord,
    CollaboratorWorkSchedule,
    CommercialEvent,
    CommercialEventCursorPosition,
    CsatContact,
    CsatEvaluation,
    CsatSummaryRecord,
    DailyPlannedWorkScheduleFact,
    DailyWorkScheduleOverride,
    DailyWorkStatusFact,
    DelayOccurrence,
    DelayReview,
    EmployeeOccurrenceReport,
    IngestionCoverageEvidence,
    OperationalCollaboratorProfile,
    PauseFact,
    ProcessingHealthRecord,
    ProcessingRun,
    ProcessingRunCursorPosition,
    ProcessingRunListRecord,
    WorkSessionFact,
)
from supervisor_ai.rules_engine import Currency, LedgerEntry, LedgerEntryType


class EventRepository(Protocol):
    def add(self, event: CommercialEvent) -> None: ...

    def get_by_id(self, event_id: str) -> CommercialEvent | None: ...

    def get_by_external_reference(
        self, external_reference: str
    ) -> CommercialEvent | None: ...

    def search(
        self,
        *,
        source: str | None,
        external_reference: str | None,
        start_date: date | None,
        end_date: date | None,
        after: CommercialEventCursorPosition | None,
        limit: int,
    ) -> tuple[CommercialEvent, ...]: ...


class ProcessingRunRepository(Protocol):
    def add(self, run: ProcessingRun) -> None: ...

    def get_by_id(self, run_id: str) -> ProcessingRun | None: ...

    def find_by_event_id(self, event_id: str) -> tuple[ProcessingRun, ...]: ...

    def search(
        self,
        *,
        source: str | None,
        external_reference: str | None,
        final_status: str | None,
        rules_engine_version: str | None,
        start_date: date | None,
        end_date: date | None,
        after: ProcessingRunCursorPosition | None,
        limit: int,
    ) -> tuple[ProcessingRunListRecord, ...]: ...


class ProcessingHealthRepository(Protocol):
    def get_processing_health(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
        rules_engine_version: str | None,
    ) -> ProcessingHealthRecord: ...


class CsatRepository(Protocol):
    def add(self, evaluation: CsatEvaluation) -> None: ...

    def get_by_id(self, evaluation_id: str) -> CsatEvaluation | None: ...

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> CsatEvaluation | None: ...

    def search(
        self,
        *,
        collaborator_id: str | None,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
        channel: str | None,
    ) -> tuple[CsatEvaluation, ...]: ...

    def summarize(
        self,
        *,
        collaborator_id: str | None,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
        channel: str | None,
    ) -> CsatSummaryRecord: ...


class CsatContactRepository(Protocol):
    def add(self, contact: CsatContact) -> None: ...

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> CsatContact | None: ...

    def search_competence(
        self, *, competence_month: date, collaborator_ids: tuple[str, ...]
    ) -> tuple[CsatContact, ...]: ...


class AttendanceRepository(Protocol):
    def add(self, attendance: AttendanceFact) -> None: ...

    def get_by_id(self, attendance_id: str) -> AttendanceFact | None: ...

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> AttendanceFact | None: ...

    def search(
        self,
        *,
        operator_id: str | None,
        customer_code: str | None,
        source: str | None,
        channel: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[AttendanceFact, ...]: ...


class IngestionCoverageRepository(Protocol):
    def add(self, evidence: IngestionCoverageEvidence) -> None: ...

    def get_by_import_reference(
        self, *, dataset: str, source: str, import_reference: str
    ) -> IngestionCoverageEvidence | None: ...

    def get_latest(
        self, *, dataset: str, source: str
    ) -> IngestionCoverageEvidence | None: ...


class DailyWorkStatusRepository(Protocol):
    def add(self, fact: DailyWorkStatusFact) -> None: ...

    def get_by_id(self, fact_id: str) -> DailyWorkStatusFact | None: ...

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> DailyWorkStatusFact | None: ...

    def get_by_collaborator_date(
        self, *, collaborator_id: str, work_date: date
    ) -> DailyWorkStatusFact | None: ...

    def search_month(
        self, *, collaborator_id: str, competence_month: date
    ) -> tuple[DailyWorkStatusFact, ...]: ...


class CollaboratorWorkScheduleRepository(Protocol):
    def add(self, schedule: CollaboratorWorkSchedule) -> None: ...
    def get_by_id(self, schedule_id: str) -> CollaboratorWorkSchedule | None: ...
    def find_for_date(
        self, *, collaborator_id: str, work_date: date
    ) -> CollaboratorWorkSchedule | None: ...
    def find_overlapping(
        self,
        *,
        collaborator_id: str,
        effective_from: date,
        effective_until: date | None,
    ) -> tuple[CollaboratorWorkSchedule, ...]: ...


class DailyPlannedWorkScheduleRepository(Protocol):
    def add(self, fact: DailyPlannedWorkScheduleFact) -> None: ...
    def get_by_id(self, fact_id: str) -> DailyPlannedWorkScheduleFact | None: ...
    def get_by_collaborator_date(
        self, *, collaborator_id: str, work_date: date
    ) -> DailyPlannedWorkScheduleFact | None: ...
    def search_competence(
        self, *, competence_month: date, collaborator_ids: tuple[str, ...]
    ) -> tuple[DailyPlannedWorkScheduleFact, ...]: ...


class DailyWorkScheduleOverrideRepository(Protocol):
    def add(self, override: DailyWorkScheduleOverride) -> None: ...
    def get_by_id(self, override_id: str) -> DailyWorkScheduleOverride | None: ...
    def get_for_date(
        self, *, collaborator_id: str, work_date: date
    ) -> DailyWorkScheduleOverride | None: ...

    def search_competence(
        self, *, competence_month: date, collaborator_ids: tuple[str, ...]
    ) -> tuple[DailyWorkScheduleOverride, ...]: ...


class EmployeeOccurrenceReportRepository(Protocol):
    def add(self, report: EmployeeOccurrenceReport) -> None: ...

    def get_by_id(self, report_id: str) -> EmployeeOccurrenceReport | None: ...

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> EmployeeOccurrenceReport | None: ...

    def search_by_collaborator_date(
        self, *, collaborator_id: str, occurrence_date: date
    ) -> tuple[EmployeeOccurrenceReport, ...]: ...


class WorkSessionRepository(Protocol):
    def add(self, fact: WorkSessionFact) -> None: ...
    def get_by_id(self, fact_id: str) -> WorkSessionFact | None: ...
    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> WorkSessionFact | None: ...
    def search_date(
        self, *, collaborator_id: str, work_date: date
    ) -> tuple[WorkSessionFact, ...]: ...


class PauseRepository(Protocol):
    def add(self, fact: PauseFact) -> None: ...
    def get_by_id(self, fact_id: str) -> PauseFact | None: ...
    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> PauseFact | None: ...
    def search_period(
        self, *, start_date: date, end_date: date
    ) -> tuple[PauseFact, ...]: ...


class DelayOccurrenceRepository(Protocol):
    def add(self, occurrence: DelayOccurrence) -> None: ...
    def get_by_id(self, occurrence_id: str) -> DelayOccurrence | None: ...
    def get_by_source_fact(
        self, *, source_fact_type: str, source_fact_id: str
    ) -> DelayOccurrence | None: ...
    def search_month(
        self, *, collaborator_id: str, competence_month: date
    ) -> tuple[DelayOccurrence, ...]: ...


class DelayReviewRepository(Protocol):
    def add(self, review: DelayReview) -> None: ...
    def get_by_id(self, review_id: str) -> DelayReview | None: ...
    def get_latest_for_occurrences(
        self, occurrence_ids: tuple[str, ...]
    ) -> tuple[DelayReview, ...]: ...


class OperationalCollaboratorProfileRepository(Protocol):
    def add(self, profile: OperationalCollaboratorProfile) -> None: ...

    def get_by_id(
        self, collaborator_id: str
    ) -> OperationalCollaboratorProfile | None: ...

    def get_by_ids(
        self, collaborator_ids: tuple[str, ...]
    ) -> tuple[OperationalCollaboratorProfile, ...]: ...

    def list_all(self) -> tuple[OperationalCollaboratorProfile, ...]: ...


class CollaboratorExternalIdentityRepository(Protocol):
    def add(self, identity: CollaboratorExternalIdentity) -> None: ...

    def get_by_source_identity(
        self, *, source: str, external_identity: str
    ) -> CollaboratorExternalIdentity | None: ...


class LedgerRepository(Protocol):
    def add(self, entry: LedgerEntry) -> None: ...

    def get_by_entry_id(self, entry_id: str) -> LedgerEntry | None: ...

    def find_credit_by_event_id(self, event_id: str) -> LedgerEntry | None: ...

    def find_by_event_id(self, event_id: str) -> tuple[LedgerEntry, ...]: ...

    def find_credits(
        self,
        *,
        beneficiary_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[LedgerEntry, ...]: ...

    def search_collaborator_timeline(
        self,
        *,
        collaborator_id: str,
        start_date: date | None,
        end_date: date | None,
        entry_type: LedgerEntryType | None,
        currency: Currency | None,
        after: CollaboratorFinancialTimelineCursorPosition | None,
        limit: int,
    ) -> tuple[CollaboratorFinancialTimelineRecord, ...]: ...


class MkAttendanceMirrorRepository(Protocol):
    def get_by_external_id(self, external_id: str) -> MkAttendanceMirror | None: ...
    def upsert(self, item: MkAttendanceMirror) -> MkUpsertOutcome: ...
    def list_open(self, *, limit: int = 1000) -> tuple[MkAttendanceMirror, ...]: ...
    def list_by_dialog_session_external_id(
        self, external_id: str
    ) -> tuple[MkAttendanceMirror, ...]: ...


class MkBotConversationMirrorRepository(Protocol):
    def get_by_external_id(
        self, external_id: str
    ) -> MkBotConversationMirror | None: ...
    def upsert(self, item: MkBotConversationMirror) -> MkUpsertOutcome: ...
    def list_open(
        self, *, limit: int = 1000
    ) -> tuple[MkBotConversationMirror, ...]: ...


class MkSyncRepository(Protocol):
    def get_state(self, *, source: str, entity_type: str) -> MkSyncState | None: ...
    def save_state(self, state: MkSyncState) -> None: ...
    def add_run(self, run: MkSyncRun) -> None: ...
    def update_run(self, run: MkSyncRun) -> None: ...
    def get_run(self, run_id: str) -> MkSyncRun | None: ...


class UnitOfWork(Protocol):
    events: EventRepository
    processing_runs: ProcessingRunRepository
    processing_health: ProcessingHealthRepository
    ledger: LedgerRepository
    csat: CsatRepository
    csat_contacts: CsatContactRepository
    attendances: AttendanceRepository
    daily_work_statuses: DailyWorkStatusRepository
    collaborator_work_schedules: CollaboratorWorkScheduleRepository
    daily_planned_work_schedules: DailyPlannedWorkScheduleRepository
    daily_work_schedule_overrides: DailyWorkScheduleOverrideRepository
    employee_occurrence_reports: EmployeeOccurrenceReportRepository
    work_sessions: WorkSessionRepository
    pauses: PauseRepository
    delay_occurrences: DelayOccurrenceRepository
    delay_reviews: DelayReviewRepository
    operational_collaborators: OperationalCollaboratorProfileRepository
    collaborator_external_identities: CollaboratorExternalIdentityRepository
    ingestion_coverages: IngestionCoverageRepository
    mk_attendances: MkAttendanceMirrorRepository
    mkbot_conversations: MkBotConversationMirrorRepository
    mk_sync: MkSyncRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...


class ProcessingRunIdGenerator(Protocol):
    def __call__(self) -> str: ...
