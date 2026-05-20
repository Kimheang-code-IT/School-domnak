"""Optional description on levels.

Revision ID: 0012_level_description
Revises: 0011_class_commission_mode
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_level_description"
down_revision: Union[str, None] = "0011_class_commission_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("levels", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("levels", "description")
