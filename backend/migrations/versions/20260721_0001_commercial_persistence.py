"""Cria persistência de eventos comerciais e remuneração.

Revision ID: 20260721_0001
Revises:
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commercial_events",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(source) > 0", name="ck_commercial_events_source"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_commercial_events_external_reference",
        "commercial_events",
        ["external_reference"],
        unique=True,
    )

    op.create_table(
        "processing_runs",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("final_status", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rules_engine_version", sa.String(length=100), nullable=False),
        sa.Column("phase_results", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("audit_references", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(final_status) > 0", name="ck_processing_runs_final_status"
        ),
        sa.CheckConstraint(
            "completed_at >= started_at", name="ck_processing_runs_time_order"
        ),
        sa.ForeignKeyConstraint(["event_id"], ["commercial_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_processing_runs_event_id", "processing_runs", ["event_id"]
    )

    op.create_table(
        "ledger_entries",
        sa.Column("entry_id", sa.String(length=255), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("beneficiary_id", sa.String(length=128), nullable=False),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posting_reference", sa.String(length=255), nullable=False),
        sa.Column(
            "remuneration_calculation_reference",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("invoice_id", sa.String(length=255), nullable=True),
        sa.Column("source_reference_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "currency IN ('BRL', 'USD')", name="ck_ledger_entries_currency"
        ),
        sa.CheckConstraint(
            "entry_type IN ('credit', 'debit', 'adjustment')",
            name="ck_ledger_entries_entry_type",
        ),
        sa.CheckConstraint(
            "amount > 0", name="ck_ledger_entries_positive_amount"
        ),
        sa.ForeignKeyConstraint(["event_id"], ["commercial_events.id"]),
        sa.PrimaryKeyConstraint("entry_id"),
    )
    op.create_index("ix_ledger_entries_event_id", "ledger_entries", ["event_id"])
    op.create_index(
        "uq_ledger_entries_credit_event",
        "ledger_entries",
        ["event_id"],
        unique=True,
        sqlite_where=sa.text("entry_type = 'credit'"),
        postgresql_where=sa.text("entry_type = 'credit'"),
    )


def downgrade() -> None:
    op.drop_index("uq_ledger_entries_credit_event", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_event_id", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index("ix_processing_runs_event_id", table_name="processing_runs")
    op.drop_table("processing_runs")
    op.drop_index(
        "uq_commercial_events_external_reference",
        table_name="commercial_events",
    )
    op.drop_table("commercial_events")
