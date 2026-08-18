"""Cria evidências auditáveis de cobertura de ingestão.

Revision ID: 20260818_0008
Revises: 20260818_0007
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0008"
down_revision: str | None = "20260818_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_coverage_evidence",
        sa.Column("dataset", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("import_reference", sa.String(length=255), nullable=False),
        sa.Column("covered_through", sa.Date(), nullable=False),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.CheckConstraint(
            "length(dataset) > 0", name="ck_ingestion_coverage_dataset"
        ),
        sa.CheckConstraint(
            "length(source) > 0", name="ck_ingestion_coverage_source"
        ),
        sa.CheckConstraint(
            "length(import_reference) > 0",
            name="ck_ingestion_coverage_import_reference",
        ),
        sa.PrimaryKeyConstraint("dataset", "source", "import_reference"),
    )
    op.create_index(
        "ix_ingestion_coverage_latest",
        "ingestion_coverage_evidence",
        ["dataset", "source", "covered_through"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ingestion_coverage_latest",
        table_name="ingestion_coverage_evidence",
    )
    op.drop_table("ingestion_coverage_evidence")
