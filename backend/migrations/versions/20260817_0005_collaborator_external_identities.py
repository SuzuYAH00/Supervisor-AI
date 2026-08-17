"""Cria identidades externas dos colaboradores.

Revision ID: 20260817_0005
Revises: 20260817_0004
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0005"
down_revision: str | None = "20260817_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collaborator_external_identities",
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_identity", sa.String(length=255), nullable=False),
        sa.Column("collaborator_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(source) > 0",
            name="ck_collaborator_external_identities_source",
        ),
        sa.CheckConstraint(
            "length(external_identity) > 0",
            name="ck_collaborator_external_identities_value",
        ),
        sa.ForeignKeyConstraint(
            ["collaborator_id"],
            ["operational_collaborator_profiles.collaborator_id"],
        ),
        sa.PrimaryKeyConstraint("source", "external_identity"),
    )


def downgrade() -> None:
    op.drop_table("collaborator_external_identities")
