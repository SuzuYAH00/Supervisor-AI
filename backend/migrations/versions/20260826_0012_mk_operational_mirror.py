"""create mutable MK operational mirror and sync state

Revision ID: 20260826_0012
Revises: 20260818_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0012"
down_revision: str | None = "20260818_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mkbot_conversation_mirror",
        sa.Column("external_id", sa.String(255), primary_key=True),
        sa.Column("protocol", sa.String(255)),
        sa.Column("person_external_id", sa.String(255)),
        sa.Column("integration_external_reference", sa.String(255)),
        sa.Column("conversation_type", sa.String(100)),
        sa.Column("sector_external_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("human_service_started_at", sa.DateTime(timezone=True)),
        sa.Column("queue_entered_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("score", sa.Integer()),
        sa.Column("final_operator_external_id", sa.String(255)),
        sa.Column("source_first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(external_id) > 0", name="ck_mkbot_conversation_external_id"
        ),
        sa.CheckConstraint(
            "source_last_seen_at >= source_first_seen_at",
            name="ck_mkbot_conversation_seen_order",
        ),
    )
    op.create_index(
        "ix_mkbot_conversation_created_at", "mkbot_conversation_mirror", ["created_at"]
    )
    op.create_index(
        "ix_mkbot_conversation_final_operator",
        "mkbot_conversation_mirror",
        ["final_operator_external_id"],
    )

    op.create_table(
        "mk_attendance_mirror",
        sa.Column("external_id", sa.String(255), primary_key=True),
        sa.Column("protocol", sa.String(255)),
        sa.Column("customer_external_id", sa.String(255)),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("opening_operator_external_id", sa.String(255)),
        sa.Column("closing_operator_external_id", sa.String(255)),
        sa.Column("process_external_id", sa.String(255)),
        sa.Column("subprocess_external_id", sa.String(255)),
        sa.Column("opening_classification_external_id", sa.String(255)),
        sa.Column("closing_classification_external_id", sa.String(255)),
        sa.Column("origin_external_id", sa.String(255)),
        sa.Column("status", sa.String(255)),
        sa.Column("is_finalized", sa.Boolean()),
        sa.Column("mk_dialog_session_external_id", sa.String(255)),
        sa.Column("source_first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(external_id) > 0", name="ck_mk_attendance_external_id"
        ),
        sa.CheckConstraint(
            "source_last_seen_at >= source_first_seen_at",
            name="ck_mk_attendance_seen_order",
        ),
    )
    op.create_index(
        "ix_mk_attendance_customer_opened",
        "mk_attendance_mirror",
        ["customer_external_id", "opened_at"],
    )
    op.create_index("ix_mk_attendance_opened_at", "mk_attendance_mirror", ["opened_at"])
    op.create_index("ix_mk_attendance_status", "mk_attendance_mirror", ["status"])
    op.create_index(
        "ix_mk_attendance_dialog",
        "mk_attendance_mirror",
        ["mk_dialog_session_external_id"],
    )

    op.create_table(
        "mk_sync_states",
        sa.Column("source", sa.String(100), primary_key=True),
        sa.Column("entity_type", sa.String(100), primary_key=True),
        sa.Column("last_pk", sa.BigInteger()),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(source) > 0", name="ck_mk_sync_state_source"),
        sa.CheckConstraint("length(entity_type) > 0", name="ck_mk_sync_state_entity"),
        sa.CheckConstraint(
            "last_pk IS NULL OR last_pk >= 0", name="ck_mk_sync_state_cursor"
        ),
        sa.CheckConstraint(
            "status IN ('idle', 'running', 'succeeded', 'failed')",
            name="ck_mk_sync_state_status",
        ),
    )

    op.create_table(
        "mk_sync_runs",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("initial_cursor", sa.BigInteger()),
        sa.Column("final_cursor", sa.BigInteger()),
        sa.Column("inserted", sa.Integer(), nullable=False),
        sa.Column("updated", sa.Integer(), nullable=False),
        sa.Column("unchanged", sa.Integer(), nullable=False),
        sa.Column("rejected", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "inserted >= 0 AND updated >= 0 AND unchanged >= 0 AND rejected >= 0",
            name="ck_mk_sync_run_counts",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')", name="ck_mk_sync_run_status"
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_mk_sync_run_time_order",
        ),
    )
    op.create_index(
        "ix_mk_sync_run_entity_started",
        "mk_sync_runs",
        ["source", "entity_type", "started_at"],
    )


def downgrade() -> None:
    op.drop_table("mk_sync_runs")
    op.drop_table("mk_sync_states")
    op.drop_table("mk_attendance_mirror")
    op.drop_table("mkbot_conversation_mirror")
