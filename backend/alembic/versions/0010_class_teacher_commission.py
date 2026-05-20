"""Add fixed teacher commission amount per class.

Revision ID: 0010_class_teacher_commission
Revises: 0009_enrollment_duration
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_class_teacher_commission"
down_revision: Union[str, None] = "0009_enrollment_duration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "classes",
        sa.Column(
            "teacher_commission",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("classes", "teacher_commission")
