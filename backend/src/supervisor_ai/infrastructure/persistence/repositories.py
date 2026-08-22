from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Select, and_, case, distinct, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

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
    CsatSummaryGroupRecord,
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
    ProcessingHealthCount,
    ProcessingHealthRecord,
    ProcessingRun,
    ProcessingRunCursorPosition,
    ProcessingRunListRecord,
    WorkSessionFact,
)
from supervisor_ai.infrastructure.persistence.mappings import (
    attendance_to_record,
    collaborator_external_identity_to_record,
    collaborator_work_schedule_to_record,
    csat_contact_to_record,
    csat_evaluation_to_record,
    daily_planned_work_schedule_to_record,
    daily_work_schedule_override_to_record,
    daily_work_status_to_record,
    delay_occurrence_to_record,
    delay_review_to_record,
    employee_occurrence_report_to_record,
    event_to_record,
    ingestion_coverage_to_record,
    ledger_entry_to_record,
    operational_collaborator_profile_to_record,
    pause_to_record,
    processing_run_to_record,
    record_to_attendance,
    record_to_collaborator_external_identity,
    record_to_collaborator_work_schedule,
    record_to_csat_contact,
    record_to_csat_evaluation,
    record_to_daily_planned_work_schedule,
    record_to_daily_work_schedule_override,
    record_to_daily_work_status,
    record_to_delay_occurrence,
    record_to_delay_review,
    record_to_employee_occurrence_report,
    record_to_event,
    record_to_ingestion_coverage,
    record_to_ledger_entry,
    record_to_operational_collaborator_profile,
    record_to_pause,
    record_to_processing_run,
    record_to_work_session,
    work_session_to_record,
)
from supervisor_ai.infrastructure.persistence.models import (
    AttendanceFactRecord,
    CollaboratorExternalIdentityRecord,
    CollaboratorWorkScheduleRecord,
    CommercialEventRecord,
    CsatContactRecord,
    CsatEvaluationRecord,
    DailyPlannedWorkScheduleRecord,
    DailyWorkScheduleOverrideRecord,
    DailyWorkStatusRecord,
    DelayOccurrenceRecord,
    DelayReviewRecord,
    EmployeeOccurrenceReportRecord,
    IngestionCoverageEvidenceRecord,
    LedgerEntryRecord,
    OperationalCollaboratorProfileRecord,
    PauseFactRecord,
    ProcessingRunRecord,
    WorkSessionFactRecord,
)
from supervisor_ai.rules_engine import Currency, LedgerEntry, LedgerEntryType


class SqlAlchemyEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, event: CommercialEvent) -> None:
        self.session.add(event_to_record(event))
        self.session.flush()

    def get_by_id(self, event_id: str) -> CommercialEvent | None:
        record = self.session.get(CommercialEventRecord, event_id)
        return None if record is None else record_to_event(record)

    def get_by_external_reference(
        self, external_reference: str
    ) -> CommercialEvent | None:
        record = self.session.scalar(
            select(CommercialEventRecord).where(
                CommercialEventRecord.external_reference == external_reference
            )
        )
        return None if record is None else record_to_event(record)

    def search(
        self,
        *,
        source: str | None,
        external_reference: str | None,
        start_date: date | None,
        end_date: date | None,
        after: CommercialEventCursorPosition | None,
        limit: int,
    ) -> tuple[CommercialEvent, ...]:
        statement = select(CommercialEventRecord)
        if source is not None:
            statement = statement.where(CommercialEventRecord.source == source)
        if external_reference is not None:
            statement = statement.where(
                CommercialEventRecord.external_reference == external_reference
            )
        if start_date is not None:
            statement = statement.where(
                CommercialEventRecord.occurred_at
                >= datetime.combine(start_date, time.min, tzinfo=UTC)
            )
        if end_date is not None:
            end_boundary = (
                datetime.combine(end_date, time.max, tzinfo=UTC)
                if end_date == date.max
                else datetime.combine(
                    end_date + timedelta(days=1), time.min, tzinfo=UTC
                )
            )
            comparison = (
                CommercialEventRecord.occurred_at <= end_boundary
                if end_date == date.max
                else CommercialEventRecord.occurred_at < end_boundary
            )
            statement = statement.where(comparison)
        if after is not None:
            statement = statement.where(
                or_(
                    CommercialEventRecord.occurred_at < after.occurred_at,
                    and_(
                        CommercialEventRecord.occurred_at == after.occurred_at,
                        CommercialEventRecord.id < after.event_id,
                    ),
                )
            )
        records = self.session.scalars(
            statement.order_by(
                CommercialEventRecord.occurred_at.desc(),
                CommercialEventRecord.id.desc(),
            ).limit(limit)
        )
        return tuple(record_to_event(record) for record in records)


class SqlAlchemyCsatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, evaluation: CsatEvaluation) -> None:
        self.session.add(csat_evaluation_to_record(evaluation))
        self.session.flush()

    def get_by_id(self, evaluation_id: str) -> CsatEvaluation | None:
        record = self.session.get(CsatEvaluationRecord, evaluation_id)
        return None if record is None else record_to_csat_evaluation(record)

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> CsatEvaluation | None:
        record = self.session.scalar(
            select(CsatEvaluationRecord).where(
                CsatEvaluationRecord.source == source,
                CsatEvaluationRecord.external_reference == external_reference,
            )
        )
        return None if record is None else record_to_csat_evaluation(record)

    def search(
        self,
        *,
        collaborator_id: str | None,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
        channel: str | None,
    ) -> tuple[CsatEvaluation, ...]:
        statement = select(CsatEvaluationRecord).where(
            *_csat_filters(
                collaborator_id=collaborator_id,
                start_date=start_date,
                end_date=end_date,
                source=source,
                channel=channel,
            )
        )
        records = self.session.scalars(
            statement.order_by(
                CsatEvaluationRecord.evaluated_at,
                CsatEvaluationRecord.id,
            )
        )
        return tuple(record_to_csat_evaluation(record) for record in records)

    def summarize(
        self,
        *,
        collaborator_id: str | None,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
        channel: str | None,
    ) -> CsatSummaryRecord:
        filters = _csat_filters(
            collaborator_id=collaborator_id,
            start_date=start_date,
            end_date=end_date,
            source=source,
            channel=channel,
        )
        total_count, total_score = self.session.execute(
            select(func.count(), func.coalesce(func.sum(CsatEvaluationRecord.score), 0))
            .select_from(CsatEvaluationRecord)
            .where(*filters)
        ).one()
        collaborator_rows = self.session.execute(
            select(
                CsatEvaluationRecord.collaborator_id,
                func.count(),
                func.sum(CsatEvaluationRecord.score),
            )
            .where(*filters)
            .group_by(CsatEvaluationRecord.collaborator_id)
            .order_by(CsatEvaluationRecord.collaborator_id)
        )
        channel_rows = self.session.execute(
            select(
                CsatEvaluationRecord.channel,
                func.count(),
                func.sum(CsatEvaluationRecord.score),
            )
            .where(*filters)
            .group_by(CsatEvaluationRecord.channel)
            .order_by(CsatEvaluationRecord.channel)
        )
        return CsatSummaryRecord(
            evaluation_count=int(total_count),
            score_total=Decimal(total_score),
            by_collaborator=tuple(
                CsatSummaryGroupRecord(str(value), int(count), Decimal(score))
                for value, count, score in collaborator_rows
            ),
            by_channel=tuple(
                CsatSummaryGroupRecord(
                    None if value is None else str(value),
                    int(count),
                    Decimal(score),
                )
                for value, count, score in channel_rows
            ),
        )


class SqlAlchemyCsatContactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, contact: CsatContact) -> None:
        self.session.add(csat_contact_to_record(contact))
        self.session.flush()

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> CsatContact | None:
        record = self.session.scalar(
            select(CsatContactRecord).where(
                CsatContactRecord.source == source,
                CsatContactRecord.external_reference == external_reference,
            )
        )
        return None if record is None else record_to_csat_contact(record)

    def search_competence(
        self, *, competence_month: date, collaborator_ids: tuple[str, ...]
    ) -> tuple[CsatContact, ...]:
        if competence_month.day != 1:
            raise ValueError("competence_month must be the first day of a month")
        if not collaborator_ids:
            return ()
        next_month = (
            date(competence_month.year + 1, 1, 1)
            if competence_month.month == 12
            else date(competence_month.year, competence_month.month + 1, 1)
        )
        records = self.session.scalars(
            select(CsatContactRecord)
            .where(
                CsatContactRecord.collaborator_id.in_(collaborator_ids),
                CsatContactRecord.occurred_on >= competence_month,
                CsatContactRecord.occurred_on < next_month,
            )
            .order_by(
                CsatContactRecord.collaborator_id,
                CsatContactRecord.occurred_on,
                CsatContactRecord.id,
            )
        )
        return tuple(record_to_csat_contact(record) for record in records)


class SqlAlchemyOperationalCollaboratorProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, profile: OperationalCollaboratorProfile) -> None:
        self.session.add(operational_collaborator_profile_to_record(profile))
        self.session.flush()

    def get_by_id(self, collaborator_id: str) -> OperationalCollaboratorProfile | None:
        record = self.session.get(OperationalCollaboratorProfileRecord, collaborator_id)
        if record is None:
            return None
        return record_to_operational_collaborator_profile(record)

    def get_by_ids(
        self, collaborator_ids: tuple[str, ...]
    ) -> tuple[OperationalCollaboratorProfile, ...]:
        if not collaborator_ids:
            return ()
        records = self.session.scalars(
            select(OperationalCollaboratorProfileRecord)
            .where(
                OperationalCollaboratorProfileRecord.collaborator_id.in_(
                    collaborator_ids
                )
            )
            .order_by(OperationalCollaboratorProfileRecord.collaborator_id)
        )
        return tuple(
            record_to_operational_collaborator_profile(record) for record in records
        )

    def list_all(self) -> tuple[OperationalCollaboratorProfile, ...]:
        records = self.session.scalars(
            select(OperationalCollaboratorProfileRecord).order_by(
                OperationalCollaboratorProfileRecord.collaborator_id
            )
        )
        return tuple(
            record_to_operational_collaborator_profile(record) for record in records
        )


class SqlAlchemyCollaboratorExternalIdentityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, identity: CollaboratorExternalIdentity) -> None:
        self.session.add(collaborator_external_identity_to_record(identity))
        self.session.flush()

    def get_by_source_identity(
        self, *, source: str, external_identity: str
    ) -> CollaboratorExternalIdentity | None:
        record = self.session.get(
            CollaboratorExternalIdentityRecord,
            (source, external_identity),
        )
        if record is None:
            return None
        return record_to_collaborator_external_identity(record)


class SqlAlchemyAttendanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, attendance: AttendanceFact) -> None:
        self.session.add(attendance_to_record(attendance))
        self.session.flush()

    def get_by_id(self, attendance_id: str) -> AttendanceFact | None:
        record = self.session.get(AttendanceFactRecord, attendance_id)
        return None if record is None else record_to_attendance(record)

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> AttendanceFact | None:
        record = self.session.scalar(
            select(AttendanceFactRecord).where(
                AttendanceFactRecord.source == source,
                AttendanceFactRecord.external_reference == external_reference,
            )
        )
        return None if record is None else record_to_attendance(record)

    def search(
        self,
        *,
        operator_id: str | None,
        customer_code: str | None,
        source: str | None,
        channel: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[AttendanceFact, ...]:
        filters: list[ColumnElement[bool]] = []
        if operator_id is not None:
            filters.append(AttendanceFactRecord.operator_id == operator_id)
        if customer_code is not None:
            filters.append(AttendanceFactRecord.customer_code == customer_code)
        if source is not None:
            filters.append(AttendanceFactRecord.source == source)
        if channel is not None:
            filters.append(AttendanceFactRecord.channel == channel)
        if start_date is not None:
            filters.append(
                AttendanceFactRecord.occurred_at
                >= datetime.combine(start_date, time.min, tzinfo=UTC)
            )
        if end_date is not None:
            filters.append(
                AttendanceFactRecord.occurred_at
                <= datetime.combine(end_date, time.max, tzinfo=UTC)
                if end_date == date.max
                else AttendanceFactRecord.occurred_at
                < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
            )
        records = self.session.scalars(
            select(AttendanceFactRecord)
            .where(*filters)
            .order_by(AttendanceFactRecord.occurred_at, AttendanceFactRecord.id)
        )
        return tuple(record_to_attendance(record) for record in records)


class SqlAlchemyDailyWorkStatusRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, fact: DailyWorkStatusFact) -> None:
        self.session.add(daily_work_status_to_record(fact))
        self.session.flush()

    def get_by_id(self, fact_id: str) -> DailyWorkStatusFact | None:
        record = self.session.get(DailyWorkStatusRecord, fact_id)
        return None if record is None else record_to_daily_work_status(record)

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> DailyWorkStatusFact | None:
        record = self.session.scalar(
            select(DailyWorkStatusRecord).where(
                DailyWorkStatusRecord.source == source,
                DailyWorkStatusRecord.external_reference == external_reference,
            )
        )
        return None if record is None else record_to_daily_work_status(record)

    def get_by_collaborator_date(
        self, *, collaborator_id: str, work_date: date
    ) -> DailyWorkStatusFact | None:
        record = self.session.scalar(
            select(DailyWorkStatusRecord).where(
                DailyWorkStatusRecord.collaborator_id == collaborator_id,
                DailyWorkStatusRecord.work_date == work_date,
            )
        )
        return None if record is None else record_to_daily_work_status(record)

    def search_month(
        self, *, collaborator_id: str, competence_month: date
    ) -> tuple[DailyWorkStatusFact, ...]:
        records = self.session.scalars(
            select(DailyWorkStatusRecord)
            .where(
                DailyWorkStatusRecord.collaborator_id == collaborator_id,
                DailyWorkStatusRecord.competence_month == competence_month,
            )
            .order_by(DailyWorkStatusRecord.work_date)
        )
        return tuple(record_to_daily_work_status(record) for record in records)

    def search_competence(
        self, *, competence_month: date, collaborator_ids: tuple[str, ...]
    ) -> tuple[DailyWorkStatusFact, ...]:
        if not collaborator_ids:
            return ()
        records = self.session.scalars(
            select(DailyWorkStatusRecord)
            .where(
                DailyWorkStatusRecord.competence_month == competence_month,
                DailyWorkStatusRecord.collaborator_id.in_(collaborator_ids),
            )
            .order_by(
                DailyWorkStatusRecord.collaborator_id,
                DailyWorkStatusRecord.work_date,
            )
        )
        return tuple(record_to_daily_work_status(record) for record in records)


class SqlAlchemyCollaboratorWorkScheduleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, schedule: CollaboratorWorkSchedule) -> None:
        self.session.add(collaborator_work_schedule_to_record(schedule))
        self.session.flush()

    def get_by_id(self, schedule_id: str) -> CollaboratorWorkSchedule | None:
        item = self.session.get(CollaboratorWorkScheduleRecord, schedule_id)
        return None if item is None else record_to_collaborator_work_schedule(item)

    def find_for_date(
        self, *, collaborator_id: str, work_date: date
    ) -> CollaboratorWorkSchedule | None:
        item = self.session.scalar(
            select(CollaboratorWorkScheduleRecord)
            .where(
                CollaboratorWorkScheduleRecord.collaborator_id == collaborator_id,
                CollaboratorWorkScheduleRecord.effective_from <= work_date,
                or_(
                    CollaboratorWorkScheduleRecord.effective_until.is_(None),
                    CollaboratorWorkScheduleRecord.effective_until >= work_date,
                ),
            )
            .order_by(CollaboratorWorkScheduleRecord.effective_from.desc())
            .limit(1)
        )
        return None if item is None else record_to_collaborator_work_schedule(item)

    def find_overlapping(
        self,
        *,
        collaborator_id: str,
        effective_from: date,
        effective_until: date | None,
    ) -> tuple[CollaboratorWorkSchedule, ...]:
        end = effective_until or date.max
        items = self.session.scalars(
            select(CollaboratorWorkScheduleRecord).where(
                CollaboratorWorkScheduleRecord.collaborator_id == collaborator_id,
                CollaboratorWorkScheduleRecord.effective_from <= end,
                or_(
                    CollaboratorWorkScheduleRecord.effective_until.is_(None),
                    CollaboratorWorkScheduleRecord.effective_until >= effective_from,
                ),
            )
        )
        return tuple(record_to_collaborator_work_schedule(item) for item in items)


class SqlAlchemyDailyPlannedWorkScheduleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, fact: DailyPlannedWorkScheduleFact) -> None:
        self.session.add(daily_planned_work_schedule_to_record(fact))
        self.session.flush()

    def get_by_id(self, fact_id: str) -> DailyPlannedWorkScheduleFact | None:
        item = self.session.get(DailyPlannedWorkScheduleRecord, fact_id)
        return None if item is None else record_to_daily_planned_work_schedule(item)

    def get_by_collaborator_date(
        self, *, collaborator_id: str, work_date: date
    ) -> DailyPlannedWorkScheduleFact | None:
        item = self.session.scalar(
            select(DailyPlannedWorkScheduleRecord).where(
                DailyPlannedWorkScheduleRecord.collaborator_id == collaborator_id,
                DailyPlannedWorkScheduleRecord.work_date == work_date,
            )
        )
        return None if item is None else record_to_daily_planned_work_schedule(item)

    def search_competence(
        self, *, competence_month: date, collaborator_ids: tuple[str, ...]
    ) -> tuple[DailyPlannedWorkScheduleFact, ...]:
        if not collaborator_ids:
            return ()
        following = date(
            competence_month.year + (competence_month.month == 12),
            competence_month.month % 12 + 1,
            1,
        )
        items = self.session.scalars(
            select(DailyPlannedWorkScheduleRecord)
            .where(
                DailyPlannedWorkScheduleRecord.collaborator_id.in_(collaborator_ids),
                DailyPlannedWorkScheduleRecord.work_date >= competence_month,
                DailyPlannedWorkScheduleRecord.work_date < following,
            )
            .order_by(
                DailyPlannedWorkScheduleRecord.collaborator_id,
                DailyPlannedWorkScheduleRecord.work_date,
            )
        )
        return tuple(record_to_daily_planned_work_schedule(item) for item in items)


class SqlAlchemyDailyWorkScheduleOverrideRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, override: DailyWorkScheduleOverride) -> None:
        self.session.add(daily_work_schedule_override_to_record(override))
        self.session.flush()

    def get_by_id(self, override_id: str) -> DailyWorkScheduleOverride | None:
        item = self.session.get(DailyWorkScheduleOverrideRecord, override_id)
        return None if item is None else record_to_daily_work_schedule_override(item)

    def get_for_date(
        self, *, collaborator_id: str, work_date: date
    ) -> DailyWorkScheduleOverride | None:
        item = self.session.scalar(
            select(DailyWorkScheduleOverrideRecord).where(
                DailyWorkScheduleOverrideRecord.collaborator_id == collaborator_id,
                DailyWorkScheduleOverrideRecord.work_date == work_date,
            )
        )
        return None if item is None else record_to_daily_work_schedule_override(item)

    def search_competence(
        self, *, competence_month: date, collaborator_ids: tuple[str, ...]
    ) -> tuple[DailyWorkScheduleOverride, ...]:
        if not collaborator_ids:
            return ()
        following = date(
            competence_month.year + (competence_month.month == 12),
            competence_month.month % 12 + 1,
            1,
        )
        items = self.session.scalars(
            select(DailyWorkScheduleOverrideRecord)
            .where(
                DailyWorkScheduleOverrideRecord.collaborator_id.in_(collaborator_ids),
                DailyWorkScheduleOverrideRecord.work_date >= competence_month,
                DailyWorkScheduleOverrideRecord.work_date < following,
            )
            .order_by(
                DailyWorkScheduleOverrideRecord.collaborator_id,
                DailyWorkScheduleOverrideRecord.work_date,
            )
        )
        return tuple(record_to_daily_work_schedule_override(item) for item in items)


class SqlAlchemyEmployeeOccurrenceReportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, report: EmployeeOccurrenceReport) -> None:
        self.session.add(employee_occurrence_report_to_record(report))
        self.session.flush()

    def get_by_id(self, report_id: str) -> EmployeeOccurrenceReport | None:
        record = self.session.get(EmployeeOccurrenceReportRecord, report_id)
        return None if record is None else record_to_employee_occurrence_report(record)

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> EmployeeOccurrenceReport | None:
        record = self.session.scalar(
            select(EmployeeOccurrenceReportRecord).where(
                EmployeeOccurrenceReportRecord.source == source,
                EmployeeOccurrenceReportRecord.external_reference == external_reference,
            )
        )
        return None if record is None else record_to_employee_occurrence_report(record)

    def search_by_collaborator_date(
        self, *, collaborator_id: str, occurrence_date: date
    ) -> tuple[EmployeeOccurrenceReport, ...]:
        records = self.session.scalars(
            select(EmployeeOccurrenceReportRecord)
            .where(
                EmployeeOccurrenceReportRecord.collaborator_id == collaborator_id,
                EmployeeOccurrenceReportRecord.occurrence_date == occurrence_date,
            )
            .order_by(
                EmployeeOccurrenceReportRecord.submitted_at,
                EmployeeOccurrenceReportRecord.id,
            )
        )
        return tuple(record_to_employee_occurrence_report(item) for item in records)


class SqlAlchemyWorkSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, fact: WorkSessionFact) -> None:
        self.session.add(work_session_to_record(fact))
        self.session.flush()

    def get_by_id(self, fact_id: str) -> WorkSessionFact | None:
        item = self.session.get(WorkSessionFactRecord, fact_id)
        return None if item is None else record_to_work_session(item)

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> WorkSessionFact | None:
        item = self.session.scalar(
            select(WorkSessionFactRecord).where(
                WorkSessionFactRecord.source == source,
                WorkSessionFactRecord.external_reference == external_reference,
            )
        )
        return None if item is None else record_to_work_session(item)

    def search_date(
        self, *, collaborator_id: str, work_date: date
    ) -> tuple[WorkSessionFact, ...]:
        operational_timezone = ZoneInfo("America/Fortaleza")
        start = datetime.combine(work_date, time.min, operational_timezone).astimezone(
            UTC
        )
        end = start + timedelta(days=1)
        items = self.session.scalars(
            select(WorkSessionFactRecord)
            .where(
                WorkSessionFactRecord.collaborator_id == collaborator_id,
                WorkSessionFactRecord.started_at >= start,
                WorkSessionFactRecord.started_at < end,
            )
            .order_by(WorkSessionFactRecord.started_at, WorkSessionFactRecord.id)
        )
        return tuple(record_to_work_session(item) for item in items)


class SqlAlchemyPauseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, fact: PauseFact) -> None:
        self.session.add(pause_to_record(fact))
        self.session.flush()

    def get_by_id(self, fact_id: str) -> PauseFact | None:
        item = self.session.get(PauseFactRecord, fact_id)
        return None if item is None else record_to_pause(item)

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> PauseFact | None:
        item = self.session.scalar(
            select(PauseFactRecord).where(
                PauseFactRecord.source == source,
                PauseFactRecord.external_reference == external_reference,
            )
        )
        return None if item is None else record_to_pause(item)

    def search_period(
        self, *, start_date: date, end_date: date
    ) -> tuple[PauseFact, ...]:
        operational_timezone = ZoneInfo("America/Fortaleza")
        start = datetime.combine(start_date, time.min, operational_timezone).astimezone(
            UTC
        )
        end = datetime.combine(
            end_date + timedelta(days=1), time.min, operational_timezone
        ).astimezone(UTC)
        items = self.session.scalars(
            select(PauseFactRecord)
            .where(
                PauseFactRecord.started_at >= start, PauseFactRecord.started_at < end
            )
            .order_by(PauseFactRecord.started_at, PauseFactRecord.id)
        )
        return tuple(record_to_pause(item) for item in items)


class SqlAlchemyDelayOccurrenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, occurrence: DelayOccurrence) -> None:
        self.session.add(delay_occurrence_to_record(occurrence))
        self.session.flush()

    def get_by_id(self, occurrence_id: str) -> DelayOccurrence | None:
        item = self.session.get(DelayOccurrenceRecord, occurrence_id)
        return None if item is None else record_to_delay_occurrence(item)

    def get_by_source_fact(
        self, *, source_fact_type: str, source_fact_id: str
    ) -> DelayOccurrence | None:
        item = self.session.scalar(
            select(DelayOccurrenceRecord).where(
                DelayOccurrenceRecord.source_fact_type == source_fact_type,
                DelayOccurrenceRecord.source_fact_id == source_fact_id,
            )
        )
        return None if item is None else record_to_delay_occurrence(item)

    def search_month(
        self, *, collaborator_id: str, competence_month: date
    ) -> tuple[DelayOccurrence, ...]:
        if competence_month.month == 12:
            following = date(competence_month.year + 1, 1, 1)
        else:
            following = date(competence_month.year, competence_month.month + 1, 1)
        items = self.session.scalars(
            select(DelayOccurrenceRecord)
            .where(
                DelayOccurrenceRecord.collaborator_id == collaborator_id,
                DelayOccurrenceRecord.occurrence_date >= competence_month,
                DelayOccurrenceRecord.occurrence_date < following,
            )
            .order_by(DelayOccurrenceRecord.occurrence_date, DelayOccurrenceRecord.id)
        )
        return tuple(record_to_delay_occurrence(item) for item in items)


class SqlAlchemyDelayReviewRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, review: DelayReview) -> None:
        self.session.add(delay_review_to_record(review))
        self.session.flush()

    def get_by_id(self, review_id: str) -> DelayReview | None:
        item = self.session.get(DelayReviewRecord, review_id)
        return None if item is None else record_to_delay_review(item)

    def get_latest_for_occurrences(
        self, occurrence_ids: tuple[str, ...]
    ) -> tuple[DelayReview, ...]:
        if not occurrence_ids:
            return ()
        items = self.session.scalars(
            select(DelayReviewRecord)
            .where(DelayReviewRecord.delay_occurrence_id.in_(occurrence_ids))
            .order_by(
                DelayReviewRecord.delay_occurrence_id,
                DelayReviewRecord.decided_at.desc(),
                DelayReviewRecord.id.desc(),
            )
        )
        latest: dict[str, DelayReview] = {}
        for item in items:
            review = record_to_delay_review(item)
            latest.setdefault(review.delay_occurrence_id, review)
        return tuple(latest.values())


class SqlAlchemyIngestionCoverageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, evidence: IngestionCoverageEvidence) -> None:
        self.session.add(ingestion_coverage_to_record(evidence))
        self.session.flush()

    def get_by_import_reference(
        self, *, dataset: str, source: str, import_reference: str
    ) -> IngestionCoverageEvidence | None:
        record = self.session.get(
            IngestionCoverageEvidenceRecord,
            (dataset, source, import_reference),
        )
        return None if record is None else record_to_ingestion_coverage(record)

    def get_latest(
        self, *, dataset: str, source: str
    ) -> IngestionCoverageEvidence | None:
        record = self.session.scalar(
            select(IngestionCoverageEvidenceRecord)
            .where(
                IngestionCoverageEvidenceRecord.dataset == dataset,
                IngestionCoverageEvidenceRecord.source == source,
            )
            .order_by(
                IngestionCoverageEvidenceRecord.covered_through.desc(),
                IngestionCoverageEvidenceRecord.recorded_at.desc(),
                IngestionCoverageEvidenceRecord.import_reference.desc(),
            )
            .limit(1)
        )
        return None if record is None else record_to_ingestion_coverage(record)


class SqlAlchemyProcessingRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run: ProcessingRun) -> None:
        self.session.add(processing_run_to_record(run))
        self.session.flush()

    def get_by_id(self, run_id: str) -> ProcessingRun | None:
        record = self.session.get(ProcessingRunRecord, run_id)
        return None if record is None else record_to_processing_run(record)

    def find_by_event_id(self, event_id: str) -> tuple[ProcessingRun, ...]:
        records = self.session.scalars(
            select(ProcessingRunRecord)
            .where(ProcessingRunRecord.event_id == event_id)
            .order_by(ProcessingRunRecord.started_at, ProcessingRunRecord.id)
        )
        return tuple(record_to_processing_run(record) for record in records)

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
    ) -> tuple[ProcessingRunListRecord, ...]:
        statement = select(
            ProcessingRunRecord.id,
            ProcessingRunRecord.event_id,
            CommercialEventRecord.source,
            CommercialEventRecord.external_reference,
            ProcessingRunRecord.started_at,
            ProcessingRunRecord.completed_at,
            ProcessingRunRecord.final_status,
            ProcessingRunRecord.rules_engine_version,
        ).join(
            CommercialEventRecord,
            CommercialEventRecord.id == ProcessingRunRecord.event_id,
        )
        statement = statement.where(
            *_processing_run_filters(
                start_date=start_date,
                end_date=end_date,
                source=source,
                rules_engine_version=rules_engine_version,
            )
        )
        if external_reference is not None:
            statement = statement.where(
                CommercialEventRecord.external_reference == external_reference
            )
        if final_status is not None:
            statement = statement.where(
                ProcessingRunRecord.final_status == final_status
            )
        if after is not None:
            statement = statement.where(
                or_(
                    ProcessingRunRecord.started_at < after.started_at,
                    and_(
                        ProcessingRunRecord.started_at == after.started_at,
                        ProcessingRunRecord.id < after.processing_run_id,
                    ),
                )
            )
        rows = self.session.execute(
            statement.order_by(
                ProcessingRunRecord.started_at.desc(),
                ProcessingRunRecord.id.desc(),
            ).limit(limit)
        )
        return tuple(
            ProcessingRunListRecord(
                processing_run_id=row.id,
                event_id=row.event_id,
                source=row.source,
                external_reference=row.external_reference,
                started_at=row.started_at,
                completed_at=row.completed_at,
                final_status=row.final_status,
                rules_engine_version=row.rules_engine_version,
            )
            for row in rows
        )


class SqlAlchemyProcessingHealthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_processing_health(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
        rules_engine_version: str | None,
    ) -> ProcessingHealthRecord:
        run_filters = _processing_run_filters(
            start_date=start_date,
            end_date=end_date,
            source=source,
            rules_engine_version=rules_engine_version,
        )
        run_source = (
            select(
                ProcessingRunRecord.event_id.label("event_id"),
                ProcessingRunRecord.final_status.label("final_status"),
                ProcessingRunRecord.rules_engine_version.label("rules_engine_version"),
            )
            .join(
                CommercialEventRecord,
                CommercialEventRecord.id == ProcessingRunRecord.event_id,
            )
            .where(*run_filters)
            .subquery()
        )
        total = self.session.scalar(select(func.count()).select_from(run_source)) or 0
        status_rows = self.session.execute(
            select(run_source.c.final_status, func.count())
            .group_by(run_source.c.final_status)
            .order_by(run_source.c.final_status)
        ).all()
        version_rows = self.session.execute(
            select(run_source.c.rules_engine_version, func.count())
            .group_by(run_source.c.rules_engine_version)
            .order_by(run_source.c.rules_engine_version)
        ).all()

        has_processing_filter = (
            start_date is not None
            or end_date is not None
            or rules_engine_version is not None
        )
        if has_processing_filter:
            cohort = select(
                distinct(run_source.c.event_id).label("event_id")
            ).subquery()
        else:
            cohort_statement = select(CommercialEventRecord.id.label("event_id"))
            if source is not None:
                cohort_statement = cohort_statement.where(
                    CommercialEventRecord.source == source
                )
            cohort = cohort_statement.subquery()

        run_counts = (
            select(
                run_source.c.event_id,
                func.count().label("run_count"),
            )
            .group_by(run_source.c.event_id)
            .subquery()
        )
        ledger_events = (
            select(LedgerEntryRecord.event_id.label("event_id"))
            .group_by(LedgerEntryRecord.event_id)
            .subquery()
        )
        metrics = self.session.execute(
            select(
                func.count(cohort.c.event_id),
                func.count(run_counts.c.event_id),
                func.coalesce(
                    func.sum(case((run_counts.c.run_count > 1, 1), else_=0)),
                    0,
                ),
                func.count(ledger_events.c.event_id),
            )
            .select_from(cohort)
            .outerjoin(
                run_counts,
                run_counts.c.event_id == cohort.c.event_id,
            )
            .outerjoin(
                ledger_events,
                ledger_events.c.event_id == cohort.c.event_id,
            )
        ).one()
        event_total = int(metrics[0])
        with_runs = int(metrics[1])
        with_ledger = int(metrics[3])
        return ProcessingHealthRecord(
            processing_run_total=int(total),
            by_final_status=tuple(
                ProcessingHealthCount(str(value), int(count))
                for value, count in status_rows
            ),
            by_rules_engine_version=tuple(
                ProcessingHealthCount(str(value), int(count))
                for value, count in version_rows
            ),
            events_with_processing_runs=with_runs,
            events_without_processing_runs=event_total - with_runs,
            events_with_multiple_processing_runs=int(metrics[2]),
            events_with_ledger_entries=with_ledger,
            events_without_ledger_entries=event_total - with_ledger,
        )


class SqlAlchemyLedgerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entry: LedgerEntry) -> None:
        self.session.add(ledger_entry_to_record(entry))
        self.session.flush()

    def get_by_entry_id(self, entry_id: str) -> LedgerEntry | None:
        record = self.session.get(LedgerEntryRecord, entry_id)
        return None if record is None else record_to_ledger_entry(record)

    def find_credit_by_event_id(self, event_id: str) -> LedgerEntry | None:
        record = self.session.scalar(
            select(LedgerEntryRecord).where(
                LedgerEntryRecord.event_id == event_id,
                LedgerEntryRecord.entry_type == LedgerEntryType.CREDIT.value,
            )
        )
        return None if record is None else record_to_ledger_entry(record)

    def find_by_event_id(self, event_id: str) -> tuple[LedgerEntry, ...]:
        records = self.session.scalars(
            select(LedgerEntryRecord)
            .where(LedgerEntryRecord.event_id == event_id)
            .order_by(LedgerEntryRecord.posted_at, LedgerEntryRecord.entry_id)
        )
        return tuple(record_to_ledger_entry(record) for record in records)

    def find_credits(
        self,
        *,
        beneficiary_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[LedgerEntry, ...]:
        statement = select(LedgerEntryRecord).where(
            LedgerEntryRecord.entry_type == LedgerEntryType.CREDIT.value
        )
        statement = _apply_credit_filters(
            statement,
            beneficiary_id=beneficiary_id,
            start_date=start_date,
            end_date=end_date,
        ).order_by(LedgerEntryRecord.posted_at, LedgerEntryRecord.entry_id)
        records = self.session.scalars(statement)
        return tuple(record_to_ledger_entry(record) for record in records)

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
    ) -> tuple[CollaboratorFinancialTimelineRecord, ...]:
        statement = (
            select(
                LedgerEntryRecord.entry_id,
                LedgerEntryRecord.posted_at,
                LedgerEntryRecord.entry_type,
                LedgerEntryRecord.amount,
                LedgerEntryRecord.currency,
                LedgerEntryRecord.invoice_id,
                LedgerEntryRecord.posting_reference,
                LedgerEntryRecord.remuneration_calculation_reference,
                LedgerEntryRecord.source_reference_ids,
                CommercialEventRecord.id,
                CommercialEventRecord.external_reference,
                CommercialEventRecord.source,
                CommercialEventRecord.occurred_at,
            )
            .join(
                CommercialEventRecord,
                CommercialEventRecord.id == LedgerEntryRecord.event_id,
            )
            .where(LedgerEntryRecord.beneficiary_id == collaborator_id)
        )
        if start_date is not None:
            statement = statement.where(
                LedgerEntryRecord.posted_at
                >= datetime.combine(start_date, time.min, tzinfo=UTC)
            )
        if end_date is not None:
            statement = statement.where(
                LedgerEntryRecord.posted_at
                <= datetime.combine(end_date, time.max, tzinfo=UTC)
                if end_date == date.max
                else LedgerEntryRecord.posted_at
                < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
            )
        if entry_type is not None:
            statement = statement.where(
                LedgerEntryRecord.entry_type == entry_type.value
            )
        if currency is not None:
            statement = statement.where(LedgerEntryRecord.currency == currency.value)
        if after is not None:
            statement = statement.where(
                or_(
                    LedgerEntryRecord.posted_at < after.posted_at,
                    and_(
                        LedgerEntryRecord.posted_at == after.posted_at,
                        LedgerEntryRecord.entry_id < after.ledger_entry_id,
                    ),
                )
            )
        rows = self.session.execute(
            statement.order_by(
                LedgerEntryRecord.posted_at.desc(),
                LedgerEntryRecord.entry_id.desc(),
            ).limit(limit)
        ).all()
        return tuple(
            CollaboratorFinancialTimelineRecord(
                ledger_entry_id=row.entry_id,
                posted_at=row.posted_at,
                entry_type=LedgerEntryType(row.entry_type),
                amount=row.amount,
                currency=Currency(row.currency),
                invoice_id=row.invoice_id,
                posting_reference=row.posting_reference,
                remuneration_calculation_reference=(
                    row.remuneration_calculation_reference
                ),
                source_reference_ids=tuple(row.source_reference_ids),
                event_id=row.id,
                external_reference=row.external_reference,
                event_source=row.source,
                event_occurred_at=row.occurred_at,
            )
            for row in rows
        )


def _apply_credit_filters(
    statement: Select[tuple[LedgerEntryRecord]],
    *,
    beneficiary_id: str | None,
    start_date: date | None,
    end_date: date | None,
) -> Select[tuple[LedgerEntryRecord]]:
    if beneficiary_id is not None:
        statement = statement.where(LedgerEntryRecord.beneficiary_id == beneficiary_id)
    if start_date is not None:
        statement = statement.where(
            LedgerEntryRecord.posted_at
            >= datetime.combine(start_date, time.min, tzinfo=UTC)
        )
    if end_date is not None:
        if end_date == date.max:
            statement = statement.where(
                LedgerEntryRecord.posted_at
                <= datetime.combine(end_date, time.max, tzinfo=UTC)
            )
        else:
            statement = statement.where(
                LedgerEntryRecord.posted_at
                < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
            )
    return statement


def _csat_filters(
    *,
    collaborator_id: str | None,
    start_date: date | None,
    end_date: date | None,
    source: str | None,
    channel: str | None,
) -> tuple[ColumnElement[bool], ...]:
    filters: list[ColumnElement[bool]] = []
    if collaborator_id is not None:
        filters.append(CsatEvaluationRecord.collaborator_id == collaborator_id)
    if start_date is not None:
        filters.append(
            CsatEvaluationRecord.evaluated_at
            >= datetime.combine(start_date, time.min, tzinfo=UTC)
        )
    if end_date is not None:
        filters.append(
            CsatEvaluationRecord.evaluated_at
            <= datetime.combine(end_date, time.max, tzinfo=UTC)
            if end_date == date.max
            else CsatEvaluationRecord.evaluated_at
            < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
        )
    if source is not None:
        filters.append(CsatEvaluationRecord.source == source)
    if channel is not None:
        filters.append(CsatEvaluationRecord.channel == channel)
    return tuple(filters)


def _processing_run_filters(
    *,
    start_date: date | None,
    end_date: date | None,
    source: str | None,
    rules_engine_version: str | None,
) -> tuple[ColumnElement[bool], ...]:
    filters: list[ColumnElement[bool]] = []
    if start_date is not None:
        filters.append(
            ProcessingRunRecord.started_at
            >= datetime.combine(start_date, time.min, tzinfo=UTC)
        )
    if end_date is not None:
        filters.append(
            ProcessingRunRecord.started_at
            <= datetime.combine(end_date, time.max, tzinfo=UTC)
            if end_date == date.max
            else ProcessingRunRecord.started_at
            < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
        )
    if source is not None:
        filters.append(CommercialEventRecord.source == source)
    if rules_engine_version is not None:
        filters.append(ProcessingRunRecord.rules_engine_version == rules_engine_version)
    return tuple(filters)
