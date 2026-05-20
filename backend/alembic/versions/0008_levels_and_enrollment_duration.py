"""levels table, classes.level_id, enrollments.duration_months

Revision ID: 0008_levels_duration
Revises: 0007_invoice_number_8_digits
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_levels_duration"
down_revision: Union[str, None] = "0007_invoice_number_8_digits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level_name_km", sa.String(length=180), nullable=False),
        sa.Column("level_name_en", sa.String(length=180), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_levels_id"), "levels", ["id"], unique=False)
    op.create_index(op.f("ix_levels_level_name_km"), "levels", ["level_name_km"], unique=False)
    op.create_index(op.f("ix_levels_level_name_en"), "levels", ["level_name_en"], unique=False)

    op.add_column("classes", sa.Column("level_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_classes_level_id", "classes", "levels", ["level_id"], ["id"])

    op.add_column("enrollments", sa.Column("duration_months", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("enrollments", "duration_months")
    op.drop_constraint("fk_classes_level_id", "classes", type_="foreignkey")
    op.drop_column("classes", "level_id")
    op.drop_table("levels")
