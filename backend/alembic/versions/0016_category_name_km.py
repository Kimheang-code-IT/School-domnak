"""Add Khmer name to categories.

Revision ID: 0016_category_name_km
Revises: 0015_drop_source_columns
Create Date: 2026-07-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_category_name_km"
down_revision: Union[str, None] = "0015_drop_source_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("name_km", sa.String(length=150), nullable=True))
    op.create_index(op.f("ix_categories_name_km"), "categories", ["name_km"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_categories_name_km"), table_name="categories")
    op.drop_column("categories", "name_km")
