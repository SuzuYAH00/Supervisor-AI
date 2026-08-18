"""persist planned work schedules and overrides

Revision ID: 20260818_0011
Revises: 20260818_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0011"
down_revision: str | None = "20260818_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    collaborator_fk = sa.ForeignKey("operational_collaborator_profiles.collaborator_id")
    op.create_table(
        "collaborator_work_schedules",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("collaborator_id", sa.String(128), collaborator_fk, nullable=False),
        sa.Column("standard_start", sa.Time(), nullable=False),
        sa.Column("standard_end", sa.Time(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date()),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_work_schedule_source_reference", "collaborator_work_schedules", ["source", "source_reference"], unique=True)
    op.create_index("ix_work_schedule_collaborator_effective", "collaborator_work_schedules", ["collaborator_id", "effective_from"])
    op.create_table(
        "daily_planned_work_schedules",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("collaborator_id", sa.String(128), sa.ForeignKey("operational_collaborator_profiles.collaborator_id"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("planned_start", sa.Time()),
        sa.Column("planned_end", sa.Time()),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=False),
        sa.Column("source_sheet", sa.String(100), nullable=False),
        sa.Column("source_cell", sa.String(20), nullable=False),
        sa.Column("unresolved_reason", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_daily_planned_schedule_collaborator_date", "daily_planned_work_schedules", ["collaborator_id", "work_date"], unique=True)
    op.create_index("uq_daily_planned_schedule_source_reference", "daily_planned_work_schedules", ["source", "source_reference"], unique=True)
    op.create_table(
        "daily_work_schedule_overrides",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("collaborator_id", sa.String(128), sa.ForeignKey("operational_collaborator_profiles.collaborator_id"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("planned_start", sa.Time(), nullable=False),
        sa.Column("planned_end", sa.Time(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_daily_work_schedule_override_date", "daily_work_schedule_overrides", ["collaborator_id", "work_date"], unique=True)


def downgrade() -> None:
    op.drop_table("daily_work_schedule_overrides")
    op.drop_table("daily_planned_work_schedules")
    op.drop_table("collaborator_work_schedules")
