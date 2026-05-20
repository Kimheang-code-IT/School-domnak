"""Teacher commission percent vs fixed USD mode on classes.

Revision ID: 0011_class_commission_mode
Revises: 0010_class_teacher_commission
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_class_commission_mode"
down_revision: Union[str, None] = "0010_class_teacher_commission"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "classes",
        sa.Column(
            "teacher_commission_mode",
            sa.String(20),
            nullable=False,
            server_default="usd",
        ),
    )
    op.add_column(
        "classes",
        sa.Column(
            "teacher_commission_percent",
            sa.Numeric(6, 2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("classes", "teacher_commission_percent")
    op.drop_column("classes", "teacher_commission_mode")
