"""persist NPX workforce facts and delay reviews

Revision ID: 20260818_0010
Revises: 20260818_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0010"
down_revision: str | None = "20260818_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("work_session_facts", *_fact_columns())
    op.create_index(
        "uq_work_session_source_reference",
        "work_session_facts",
        ["source", "external_reference"],
        unique=True,
    )
    op.create_index(
        "ix_work_session_collaborator_started",
        "work_session_facts",
        ["collaborator_id", "started_at"],
    )
    pause_columns = _fact_columns()
    pause_columns.insert(7, sa.Column("pause_type", sa.String(255), nullable=False))
    pause_columns.append(sa.Column("supervisor_released", sa.String(255)))
    op.create_table("pause_facts", *pause_columns)
    op.create_index(
        "uq_pause_source_reference",
        "pause_facts",
        ["source", "external_reference"],
        unique=True,
    )
    op.create_index(
        "ix_pause_collaborator_started",
        "pause_facts",
        ["collaborator_id", "started_at"],
    )
    op.create_table(
        "delay_occurrences",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column(
            "collaborator_id",
            sa.String(128),
            sa.ForeignKey("operational_collaborator_profiles.collaborator_id"),
            nullable=False,
        ),
        sa.Column("occurrence_date", sa.Date(), nullable=False),
        sa.Column("occurrence_type", sa.String(30), nullable=False),
        sa.Column("source_fact_type", sa.String(30), nullable=False),
        sa.Column("source_fact_id", sa.String(128), nullable=False),
        sa.Column("observed_seconds", sa.Integer(), nullable=False),
        sa.Column("applied_limit_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_delay_occurrence_source_fact",
        "delay_occurrences",
        ["source_fact_type", "source_fact_id"],
        unique=True,
    )
    op.create_index(
        "ix_delay_occurrence_collaborator_date",
        "delay_occurrences",
        ["collaborator_id", "occurrence_date"],
    )
    op.create_table(
        "delay_reviews",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column(
            "delay_occurrence_id",
            sa.String(128),
            sa.ForeignKey("delay_occurrences.id"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_by", sa.String(128), nullable=False),
        sa.Column(
            "employee_occurrence_report_id",
            sa.String(128),
            sa.ForeignKey("employee_occurrence_reports.id"),
        ),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_delay_review_occurrence_decided",
        "delay_reviews",
        ["delay_occurrence_id", "decided_at"],
    )


def downgrade() -> None:
    op.drop_table("delay_reviews")
    op.drop_table("delay_occurrences")
    op.drop_table("pause_facts")
    op.drop_table("work_session_facts")


def _fact_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("external_reference", sa.String(255), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column(
            "collaborator_id",
            sa.String(128),
            sa.ForeignKey("operational_collaborator_profiles.collaborator_id"),
            nullable=False,
        ),
        sa.Column("external_collaborator_identity", sa.String(255), nullable=False),
        sa.Column("external_agent_id", sa.String(100)),
        sa.Column("queue", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("source_extract_reference", sa.String(255), nullable=False),
        sa.Column("source_sheet", sa.String(100), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]
