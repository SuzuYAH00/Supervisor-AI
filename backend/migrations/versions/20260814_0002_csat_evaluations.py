"""Cria persistência factual de avaliações CSAT.

Revision ID: 20260814_0002
Revises: 20260721_0001
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0002"
down_revision: str | None = "20260721_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "csat_evaluations",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("collaborator_id", sa.String(length=128), nullable=False),
        sa.Column("channel", sa.String(length=100), nullable=True),
        sa.Column("score", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(collaborator_id) > 0",
            name="ck_csat_evaluations_collaborator_id",
        ),
        sa.CheckConstraint(
            "length(source) > 0", name="ck_csat_evaluations_source"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_csat_evaluations_source_reference",
        "csat_evaluations",
        ["source", "external_reference"],
        unique=True,
    )
    op.create_index(
        "ix_csat_evaluations_collaborator_evaluated_at",
        "csat_evaluations",
        ["collaborator_id", "evaluated_at"],
        unique=False,
    )
    op.create_index(
        "ix_csat_evaluations_evaluated_at",
        "csat_evaluations",
        ["evaluated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_csat_evaluations_evaluated_at", table_name="csat_evaluations"
    )
    op.drop_index(
        "ix_csat_evaluations_collaborator_evaluated_at",
        table_name="csat_evaluations",
    )
    op.drop_index(
        "uq_csat_evaluations_source_reference",
        table_name="csat_evaluations",
    )
    op.drop_table("csat_evaluations")
