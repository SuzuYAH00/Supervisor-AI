from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from supervisor_ai.database.base import Base


class UTCDateTime(TypeDecorator[datetime]):
    """Mantém o contrato UTC aware inclusive no SQLite."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        del dialect
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        return value.astimezone(UTC)

    def process_result_value(
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        del dialect
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)


class CommercialEventRecord(Base):
    __tablename__ = "commercial_events"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(source) > 0", name="ck_commercial_events_source"),
        Index(
            "uq_commercial_events_external_reference",
            "external_reference",
            unique=True,
        ),
    )


class ProcessingRunRecord(Base):
    __tablename__ = "processing_runs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("commercial_events.id"), nullable=False, index=True
    )
    final_status: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    rules_engine_version: Mapped[str] = mapped_column(String(100), nullable=False)
    phase_results: Mapped[list[object]] = mapped_column(JSON, nullable=False)
    warnings: Mapped[list[object]] = mapped_column(JSON, nullable=False)
    audit_references: Mapped[list[object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "length(final_status) > 0", name="ck_processing_runs_final_status"
        ),
        CheckConstraint(
            "completed_at >= started_at", name="ck_processing_runs_time_order"
        ),
    )


class LedgerEntryRecord(Base):
    __tablename__ = "ledger_entries"

    entry_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("commercial_events.id"), nullable=False, index=True
    )
    beneficiary_id: Mapped[str] = mapped_column(String(128), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    posted_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    posting_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    remuneration_calculation_reference: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_reference_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ledger_entries_positive_amount"),
        CheckConstraint(
            "entry_type IN ('credit', 'debit', 'adjustment')",
            name="ck_ledger_entries_entry_type",
        ),
        CheckConstraint(
            "currency IN ('BRL', 'USD')", name="ck_ledger_entries_currency"
        ),
        Index(
            "uq_ledger_entries_credit_event",
            "event_id",
            unique=True,
            sqlite_where=text("entry_type = 'credit'"),
            postgresql_where=text("entry_type = 'credit'"),
        ),
    )


class CsatEvaluationRecord(Base):
    __tablename__ = "csat_evaluations"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    collaborator_id: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(source) > 0", name="ck_csat_evaluations_source"),
        CheckConstraint(
            "length(collaborator_id) > 0",
            name="ck_csat_evaluations_collaborator_id",
        ),
        Index(
            "uq_csat_evaluations_source_reference",
            "source",
            "external_reference",
            unique=True,
        ),
        Index(
            "ix_csat_evaluations_collaborator_evaluated_at",
            "collaborator_id",
            "evaluated_at",
        ),
        Index("ix_csat_evaluations_evaluated_at", "evaluated_at"),
    )


class CsatContactRecord(Base):
    __tablename__ = "csat_contacts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"),
        nullable=False,
    )
    external_operator_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_channel: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    source_context: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(source) > 0", name="ck_csat_contacts_source"),
        CheckConstraint(
            "source_channel IN ('chat', 'phone')",
            name="ck_csat_contacts_source_channel",
        ),
        CheckConstraint(
            "score IS NULL OR (source_channel = 'chat' AND score >= 0 AND score <= 5) "
            "OR (source_channel = 'phone' AND score >= 1 AND score <= 5)",
            name="ck_csat_contacts_score_scale",
        ),
        Index(
            "uq_csat_contacts_source_reference",
            "source",
            "external_reference",
            unique=True,
        ),
        Index(
            "ix_csat_contacts_collaborator_occurred_on",
            "collaborator_id",
            "occurred_on",
        ),
    )


class OperationalCollaboratorProfileRecord(Base):
    __tablename__ = "operational_collaborator_profiles"

    collaborator_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    competitive_channel: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "length(collaborator_id) > 0",
            name="ck_operational_collaborator_profiles_id",
        ),
        CheckConstraint(
            "competitive_channel IN ('chat', 'phone')",
            name="ck_operational_collaborator_profiles_channel",
        ),
    )


class CollaboratorExternalIdentityRecord(Base):
    __tablename__ = "collaborator_external_identities"

    source: Mapped[str] = mapped_column(String(100), primary_key=True)
    external_identity: Mapped[str] = mapped_column(String(255), primary_key=True)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "length(source) > 0",
            name="ck_collaborator_external_identities_source",
        ),
        CheckConstraint(
            "length(external_identity) > 0",
            name="ck_collaborator_external_identities_value",
        ),
    )


class AttendanceFactRecord(Base):
    __tablename__ = "attendance_facts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_code: Mapped[str] = mapped_column(String(128), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    process_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    process_description: Mapped[str] = mapped_column(String(255), nullable=False)
    opening_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    opening_description: Mapped[str] = mapped_column(String(255), nullable=False)
    closing_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    closing_description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(source) > 0", name="ck_attendance_facts_source"),
        CheckConstraint(
            "length(customer_code) > 0",
            name="ck_attendance_facts_customer_code",
        ),
        CheckConstraint(
            "length(operator_id) > 0", name="ck_attendance_facts_operator_id"
        ),
        Index(
            "uq_attendance_facts_source_reference",
            "source",
            "external_reference",
            unique=True,
        ),
        Index(
            "ix_attendance_facts_customer_occurred_at",
            "customer_code",
            "occurred_at",
        ),
        Index(
            "ix_attendance_facts_operator_occurred_at",
            "operator_id",
            "occurred_at",
        ),
    )


class IngestionCoverageEvidenceRecord(Base):
    __tablename__ = "ingestion_coverage_evidence"

    dataset: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(String(100), primary_key=True)
    import_reference: Mapped[str] = mapped_column(String(255), primary_key=True)
    covered_through: Mapped[date] = mapped_column(Date(), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    __table_args__ = (
        CheckConstraint("length(dataset) > 0", name="ck_ingestion_coverage_dataset"),
        CheckConstraint("length(source) > 0", name="ck_ingestion_coverage_source"),
        CheckConstraint(
            "length(import_reference) > 0",
            name="ck_ingestion_coverage_import_reference",
        ),
        Index(
            "ix_ingestion_coverage_latest",
            "dataset",
            "source",
            "covered_through",
        ),
    )


class DailyWorkStatusRecord(Base):
    __tablename__ = "daily_work_statuses"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"),
        nullable=False,
    )
    work_date: Mapped[date] = mapped_column(Date(), nullable=False)
    competence_month: Mapped[date] = mapped_column(Date(), nullable=False)
    raw_code: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    source_cell: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(raw_code) > 0", name="ck_daily_work_status_code"),
        CheckConstraint("length(source) > 0", name="ck_daily_work_status_source"),
        CheckConstraint(
            "length(external_reference) > 0",
            name="ck_daily_work_status_external_reference",
        ),
        Index(
            "uq_daily_work_status_source_reference",
            "source",
            "external_reference",
            unique=True,
        ),
        Index(
            "uq_daily_work_status_collaborator_date",
            "collaborator_id",
            "work_date",
            unique=True,
        ),
        Index(
            "ix_daily_work_status_collaborator_competence",
            "collaborator_id",
            "competence_month",
        ),
    )


class CollaboratorWorkScheduleRecord(Base):
    __tablename__ = "collaborator_work_schedules"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"), nullable=False
    )
    standard_start: Mapped[time] = mapped_column(Time(), nullable=False)
    standard_end: Mapped[time] = mapped_column(Time(), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date(), nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date())
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )
    __table_args__ = (
        Index(
            "uq_work_schedule_source_reference",
            "source",
            "source_reference",
            unique=True,
        ),
        Index(
            "ix_work_schedule_collaborator_effective",
            "collaborator_id",
            "effective_from",
        ),
    )


class DailyPlannedWorkScheduleRecord(Base):
    __tablename__ = "daily_planned_work_schedules"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"), nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date(), nullable=False)
    planned_start: Mapped[time | None] = mapped_column(Time())
    planned_end: Mapped[time | None] = mapped_column(Time())
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    source_cell: Mapped[str] = mapped_column(String(20), nullable=False)
    unresolved_reason: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )
    __table_args__ = (
        Index(
            "uq_daily_planned_schedule_collaborator_date",
            "collaborator_id",
            "work_date",
            unique=True,
        ),
        Index(
            "uq_daily_planned_schedule_source_reference",
            "source",
            "source_reference",
            unique=True,
        ),
    )


class DailyWorkScheduleOverrideRecord(Base):
    __tablename__ = "daily_work_schedule_overrides"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"), nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date(), nullable=False)
    planned_start: Mapped[time] = mapped_column(Time(), nullable=False)
    planned_end: Mapped[time] = mapped_column(Time(), nullable=False)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )
    __table_args__ = (
        Index(
            "uq_daily_work_schedule_override_date",
            "collaborator_id",
            "work_date",
            unique=True,
        ),
    )


class EmployeeOccurrenceReportRecord(Base):
    __tablename__ = "employee_occurrence_reports"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"),
        nullable=False,
    )
    external_collaborator_identity: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    occurrence_date: Mapped[date] = mapped_column(Date(), nullable=False)
    reason_text: Mapped[str] = mapped_column(Text(), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    source_row: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )
    __table_args__ = (
        CheckConstraint(
            "length(source) > 0", name="ck_employee_occurrence_reports_source"
        ),
        CheckConstraint(
            "length(reason_text) > 0", name="ck_employee_occurrence_reports_reason"
        ),
        CheckConstraint(
            "source_row >= 2", name="ck_employee_occurrence_reports_source_row"
        ),
        Index(
            "uq_employee_occurrence_reports_source_reference",
            "source",
            "external_reference",
            unique=True,
        ),
        Index(
            "ix_employee_occurrence_reports_collaborator_date",
            "collaborator_id",
            "occurrence_date",
        ),
    )


class WorkSessionFactRecord(Base):
    __tablename__ = "work_session_facts"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"), nullable=False
    )
    external_collaborator_identity: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    external_agent_id: Mapped[str | None] = mapped_column(String(100))
    queue: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(nullable=False)
    source_extract_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    source_row: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )
    __table_args__ = (
        Index(
            "uq_work_session_source_reference",
            "source",
            "external_reference",
            unique=True,
        ),
        Index("ix_work_session_collaborator_started", "collaborator_id", "started_at"),
    )


class PauseFactRecord(Base):
    __tablename__ = "pause_facts"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    external_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"), nullable=False
    )
    external_collaborator_identity: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    external_agent_id: Mapped[str | None] = mapped_column(String(100))
    queue: Mapped[str] = mapped_column(String(255), nullable=False)
    pause_type: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(nullable=False)
    supervisor_released: Mapped[str | None] = mapped_column(String(255))
    source_extract_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    source_row: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )
    __table_args__ = (
        Index("uq_pause_source_reference", "source", "external_reference", unique=True),
        Index("ix_pause_collaborator_started", "collaborator_id", "started_at"),
    )


class DelayOccurrenceRecord(Base):
    __tablename__ = "delay_occurrences"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    collaborator_id: Mapped[str] = mapped_column(
        ForeignKey("operational_collaborator_profiles.collaborator_id"), nullable=False
    )
    occurrence_date: Mapped[date] = mapped_column(Date(), nullable=False)
    occurrence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_fact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_fact_id: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_seconds: Mapped[int] = mapped_column(nullable=False)
    applied_limit_seconds: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )
    __table_args__ = (
        Index(
            "uq_delay_occurrence_source_fact",
            "source_fact_type",
            "source_fact_id",
            unique=True,
        ),
        Index(
            "ix_delay_occurrence_collaborator_date",
            "collaborator_id",
            "occurrence_date",
        ),
    )


class DelayReviewRecord(Base):
    __tablename__ = "delay_reviews"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    delay_occurrence_id: Mapped[str] = mapped_column(
        ForeignKey("delay_occurrences.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    decided_by: Mapped[str] = mapped_column(String(128), nullable=False)
    employee_occurrence_report_id: Mapped[str | None] = mapped_column(
        ForeignKey("employee_occurrence_reports.id")
    )
    note: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )
    __table_args__ = (
        Index(
            "ix_delay_review_occurrence_decided", "delay_occurrence_id", "decided_at"
        ),
    )


class MkAttendanceMirrorRecord(Base):
    __tablename__ = "mk_attendance_mirror"

    external_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    protocol: Mapped[str | None] = mapped_column(String(255))
    customer_external_id: Mapped[str | None] = mapped_column(String(255))
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    opening_operator_external_id: Mapped[str | None] = mapped_column(String(255))
    closing_operator_external_id: Mapped[str | None] = mapped_column(String(255))
    process_external_id: Mapped[str | None] = mapped_column(String(255))
    subprocess_external_id: Mapped[str | None] = mapped_column(String(255))
    opening_classification_external_id: Mapped[str | None] = mapped_column(String(255))
    closing_classification_external_id: Mapped[str | None] = mapped_column(String(255))
    origin_external_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(255))
    is_finalized: Mapped[bool | None] = mapped_column()
    mk_dialog_session_external_id: Mapped[str | None] = mapped_column(String(255))
    source_first_seen_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False
    )
    source_last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    local_created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    local_updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    __table_args__ = (
        CheckConstraint("length(external_id) > 0", name="ck_mk_attendance_external_id"),
        CheckConstraint(
            "source_last_seen_at >= source_first_seen_at",
            name="ck_mk_attendance_seen_order",
        ),
        Index("ix_mk_attendance_customer_opened", "customer_external_id", "opened_at"),
        Index("ix_mk_attendance_opened_at", "opened_at"),
        Index("ix_mk_attendance_status", "status"),
        Index("ix_mk_attendance_dialog", "mk_dialog_session_external_id"),
    )


class MkBotConversationMirrorRecord(Base):
    __tablename__ = "mkbot_conversation_mirror"

    external_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    protocol: Mapped[str | None] = mapped_column(String(255))
    person_external_id: Mapped[str | None] = mapped_column(String(255))
    integration_external_reference: Mapped[str | None] = mapped_column(String(255))
    conversation_type: Mapped[str | None] = mapped_column(String(100))
    sector_external_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    human_service_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    queue_entered_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    score: Mapped[int | None] = mapped_column()
    final_operator_external_id: Mapped[str | None] = mapped_column(String(255))
    source_first_seen_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False
    )
    source_last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    local_created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    local_updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "length(external_id) > 0", name="ck_mkbot_conversation_external_id"
        ),
        CheckConstraint(
            "source_last_seen_at >= source_first_seen_at",
            name="ck_mkbot_conversation_seen_order",
        ),
        Index("ix_mkbot_conversation_created_at", "created_at"),
        Index("ix_mkbot_conversation_final_operator", "final_operator_external_id"),
    )


class MkSyncStateRecord(Base):
    __tablename__ = "mk_sync_states"

    source: Mapped[str] = mapped_column(String(100), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(100), primary_key=True)
    last_pk: Mapped[int | None] = mapped_column(BigInteger())
    last_success_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    __table_args__ = (
        CheckConstraint("length(source) > 0", name="ck_mk_sync_state_source"),
        CheckConstraint("length(entity_type) > 0", name="ck_mk_sync_state_entity"),
        CheckConstraint(
            "last_pk IS NULL OR last_pk >= 0", name="ck_mk_sync_state_cursor"
        ),
        CheckConstraint(
            "status IN ('idle', 'running', 'succeeded', 'failed')",
            name="ck_mk_sync_state_status",
        ),
    )


class MkSyncRunRecord(Base):
    __tablename__ = "mk_sync_runs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    initial_cursor: Mapped[int | None] = mapped_column(BigInteger())
    final_cursor: Mapped[int | None] = mapped_column(BigInteger())
    inserted: Mapped[int] = mapped_column(nullable=False)
    updated: Mapped[int] = mapped_column(nullable=False)
    unchanged: Mapped[int] = mapped_column(nullable=False)
    rejected: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    error: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "inserted >= 0 AND updated >= 0 AND unchanged >= 0 AND rejected >= 0",
            name="ck_mk_sync_run_counts",
        ),
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_mk_sync_run_status",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_mk_sync_run_time_order",
        ),
        Index("ix_mk_sync_run_entity_started", "source", "entity_type", "started_at"),
    )
