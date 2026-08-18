"""Cria persistência canônica de contatos CSAT.

Revision ID: 20260818_0007
Revises: 20260817_0006
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0007"
down_revision: str | None = "20260817_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "csat_contacts",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("collaborator_id", sa.String(length=128), nullable=False),
        sa.Column(
            "external_operator_identity", sa.String(length=255), nullable=False
        ),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("source_channel", sa.String(length=10), nullable=False),
        sa.Column("score", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("source_context", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("length(source) > 0", name="ck_csat_contacts_source"),
        sa.CheckConstraint(
            "source_channel IN ('chat', 'phone')",
            name="ck_csat_contacts_source_channel",
        ),
        sa.CheckConstraint(
            "score IS NULL OR (source_channel = 'chat' AND score >= 0 "
            "AND score <= 5) OR (source_channel = 'phone' AND score >= 1 "
            "AND score <= 5)",
            name="ck_csat_contacts_score_scale",
        ),
        sa.ForeignKeyConstraint(
            ["collaborator_id"],
            ["operational_collaborator_profiles.collaborator_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_csat_contacts_source_reference",
        "csat_contacts",
        ["source", "external_reference"],
        unique=True,
    )
    op.create_index(
        "ix_csat_contacts_collaborator_occurred_on",
        "csat_contacts",
        ["collaborator_id", "occurred_on"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_csat_contacts_collaborator_occurred_on",
        table_name="csat_contacts",
    )
    op.drop_index(
        "uq_csat_contacts_source_reference", table_name="csat_contacts"
    )
    op.drop_table("csat_contacts")
