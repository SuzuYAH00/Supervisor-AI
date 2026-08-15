"""Cria persistência factual de atendimentos para reincidência.

Revision ID: 20260814_0003
Revises: 20260814_0002
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0003"
down_revision: str | None = "20260814_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attendance_facts",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("customer_code", sa.String(length=128), nullable=False),
        sa.Column("operator_id", sa.String(length=128), nullable=False),
        sa.Column("channel", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("process_code", sa.String(length=20), nullable=True),
        sa.Column("process_description", sa.String(length=255), nullable=False),
        sa.Column("opening_code", sa.String(length=20), nullable=True),
        sa.Column("opening_description", sa.String(length=255), nullable=False),
        sa.Column("closing_code", sa.String(length=20), nullable=True),
        sa.Column("closing_description", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(customer_code) > 0", name="ck_attendance_facts_customer_code"
        ),
        sa.CheckConstraint(
            "length(operator_id) > 0", name="ck_attendance_facts_operator_id"
        ),
        sa.CheckConstraint(
            "length(source) > 0", name="ck_attendance_facts_source"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_attendance_facts_source_reference",
        "attendance_facts",
        ["source", "external_reference"],
        unique=True,
    )
    op.create_index(
        "ix_attendance_facts_customer_occurred_at",
        "attendance_facts",
        ["customer_code", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_facts_operator_occurred_at",
        "attendance_facts",
        ["operator_id", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attendance_facts_operator_occurred_at", table_name="attendance_facts"
    )
    op.drop_index(
        "ix_attendance_facts_customer_occurred_at", table_name="attendance_facts"
    )
    op.drop_index(
        "uq_attendance_facts_source_reference", table_name="attendance_facts"
    )
    op.drop_table("attendance_facts")
