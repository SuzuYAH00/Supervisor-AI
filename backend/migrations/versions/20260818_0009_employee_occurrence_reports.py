"""Cria fatos declarados de ocorrências de colaboradores.

Revision ID: 20260818_0009
Revises: 20260818_0008
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0009"
down_revision: str | None = "20260818_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employee_occurrence_reports",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("collaborator_id", sa.String(length=128), nullable=False),
        sa.Column(
            "external_collaborator_identity",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_date", sa.Date(), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("source_sheet", sa.String(length=100), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(source) > 0", name="ck_employee_occurrence_reports_source"
        ),
        sa.CheckConstraint(
            "length(reason_text) > 0",
            name="ck_employee_occurrence_reports_reason",
        ),
        sa.CheckConstraint(
            "source_row >= 2", name="ck_employee_occurrence_reports_source_row"
        ),
        sa.ForeignKeyConstraint(
            ["collaborator_id"],
            ["operational_collaborator_profiles.collaborator_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_employee_occurrence_reports_source_reference",
        "employee_occurrence_reports",
        ["source", "external_reference"],
        unique=True,
    )
    op.create_index(
        "ix_employee_occurrence_reports_collaborator_date",
        "employee_occurrence_reports",
        ["collaborator_id", "occurrence_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employee_occurrence_reports_collaborator_date",
        table_name="employee_occurrence_reports",
    )
    op.drop_index(
        "uq_employee_occurrence_reports_source_reference",
        table_name="employee_occurrence_reports",
    )
    op.drop_table("employee_occurrence_reports")
