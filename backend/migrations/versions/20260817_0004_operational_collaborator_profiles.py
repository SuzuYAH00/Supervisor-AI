"""Cria perfis operacionais mínimos dos colaboradores.

Revision ID: 20260817_0004
Revises: 20260814_0003
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0004"
down_revision: str | None = "20260814_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operational_collaborator_profiles",
        sa.Column("collaborator_id", sa.String(length=128), nullable=False),
        sa.Column("competitive_channel", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(collaborator_id) > 0",
            name="ck_operational_collaborator_profiles_id",
        ),
        sa.CheckConstraint(
            "competitive_channel IN ('chat', 'phone')",
            name="ck_operational_collaborator_profiles_channel",
        ),
        sa.PrimaryKeyConstraint("collaborator_id"),
    )


def downgrade() -> None:
    op.drop_table("operational_collaborator_profiles")
