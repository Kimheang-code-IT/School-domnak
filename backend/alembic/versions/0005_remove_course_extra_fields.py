"""remove course extra fields

Revision ID: 0005_remove_course_extra_fields
Revises: 0004_refresh_tokens
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

revision: str = "0005_remove_course_extra_fields"
down_revision: Union[str, None] = "0004_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("courses")}
    drop_columns = [name for name in ["shift", "time", "category_id"] if name in columns]
    if not drop_columns:
        return
    with op.batch_alter_table("courses") as batch_op:
        for name in drop_columns:
            batch_op.drop_column(name)


def downgrade() -> None:
    # Course shift/time/category were removed from the API and are intentionally not restored.
    pass
