"""Cria fatos diários canônicos de presença laboral.

Revision ID: 20260817_0006
Revises: 20260817_0005
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0006"
down_revision: str | None = "20260817_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_work_statuses",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("collaborator_id", sa.String(length=128), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("competence_month", sa.Date(), nullable=False),
        sa.Column("raw_code", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=False),
        sa.Column("source_sheet", sa.String(length=100), nullable=False),
        sa.Column("source_cell", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(raw_code) > 0", name="ck_daily_work_status_code"
        ),
        sa.CheckConstraint(
            "length(source) > 0", name="ck_daily_work_status_source"
        ),
        sa.CheckConstraint(
            "length(external_reference) > 0",
            name="ck_daily_work_status_external_reference",
        ),
        sa.ForeignKeyConstraint(
            ["collaborator_id"],
            ["operational_collaborator_profiles.collaborator_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_daily_work_status_source_reference",
        "daily_work_statuses",
        ["source", "external_reference"],
        unique=True,
    )
    op.create_index(
        "uq_daily_work_status_collaborator_date",
        "daily_work_statuses",
        ["collaborator_id", "work_date"],
        unique=True,
    )
    op.create_index(
        "ix_daily_work_status_collaborator_competence",
        "daily_work_statuses",
        ["collaborator_id", "competence_month"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_daily_work_status_collaborator_competence",
        table_name="daily_work_statuses",
    )
    op.drop_index(
        "uq_daily_work_status_collaborator_date",
        table_name="daily_work_statuses",
    )
    op.drop_index(
        "uq_daily_work_status_source_reference",
        table_name="daily_work_statuses",
    )
    op.drop_table("daily_work_statuses")
