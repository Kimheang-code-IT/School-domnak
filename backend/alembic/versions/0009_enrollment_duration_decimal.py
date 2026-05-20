"""enrollments.duration_months as decimal for partial months (e.g. 1.5)

Revision ID: 0009_enrollment_duration
Revises: 0008_levels_duration
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_enrollment_duration"
down_revision: Union[str, None] = "0008_levels_duration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "enrollments",
        "duration_months",
        existing_type=sa.Integer(),
        type_=sa.Numeric(6, 2),
        existing_nullable=True,
        postgresql_using="duration_months::numeric(6,2)",
    )


def downgrade() -> None:
    op.alter_column(
        "enrollments",
        "duration_months",
        existing_type=sa.Numeric(6, 2),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="round(duration_months)::integer",
    )
