"""create mutable MK commercial mirrors

Revision ID: 20260827_0013
Revises: 20260826_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0013"
down_revision: str | None = "20260826_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _seen_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("source_first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "mk_plan_mirror",
        sa.Column("external_id", sa.String(255), primary_key=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("monthly_value", sa.Numeric(14, 2)),
        sa.Column("download_speed", sa.BigInteger()),
        sa.Column("upload_speed", sa.BigInteger()),
        sa.Column("formatted_speeds", sa.String(500)),
        *_seen_columns(),
    )
    op.create_table(
        "mk_contract_mirror",
        sa.Column("external_id", sa.String(255), primary_key=True),
        sa.Column("customer_external_id", sa.String(255), nullable=False),
        sa.Column("current_plan_external_id", sa.String(255), nullable=False),
        sa.Column("cancelled", sa.String(20)),
        sa.Column("suspended", sa.String(20)),
        sa.Column("joined_on", sa.Date()),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        *_seen_columns(),
    )
    op.create_index(
        "ix_mk_contract_customer", "mk_contract_mirror", ["customer_external_id"]
    )
    op.create_index(
        "ix_mk_contract_current_plan",
        "mk_contract_mirror",
        ["current_plan_external_id"],
    )
    op.create_table(
        "mk_contract_plan_change_mirror",
        sa.Column("external_id", sa.String(255), primary_key=True),
        sa.Column("contract_external_id", sa.String(255), nullable=False),
        sa.Column("operation_code", sa.Integer(), nullable=False),
        sa.Column("old_plan_external_id", sa.String(255)),
        sa.Column("new_plan_external_id", sa.String(255)),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by_login", sa.String(255), nullable=False),
        sa.Column("changed_by_operator_external_id", sa.String(255)),
        sa.Column("value_delta", sa.Numeric(14, 2)),
        sa.Column("extra_context", sa.Text()),
        *_seen_columns(),
    )
    for name, columns in (
        ("ix_mk_plan_change_contract_changed", ["contract_external_id", "changed_at"]),
        ("ix_mk_plan_change_operation", ["operation_code"]),
        ("ix_mk_plan_change_old_plan", ["old_plan_external_id"]),
        ("ix_mk_plan_change_new_plan", ["new_plan_external_id"]),
        ("ix_mk_plan_change_operator", ["changed_by_operator_external_id"]),
    ):
        op.create_index(name, "mk_contract_plan_change_mirror", columns)


def downgrade() -> None:
    op.drop_table("mk_contract_plan_change_mirror")
    op.drop_table("mk_contract_mirror")
    op.drop_table("mk_plan_mirror")
