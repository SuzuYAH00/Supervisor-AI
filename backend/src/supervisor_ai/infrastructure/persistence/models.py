from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
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
