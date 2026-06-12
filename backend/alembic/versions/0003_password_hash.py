"""password hash column

Revision ID: 0003_password_hash
Revises: 0002_role_permissions
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

revision: str = "0003_password_hash"
down_revision: Union[str, None] = "0002_role_permissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "hashed_password" in columns and "password_hash" not in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("hashed_password", new_column_name="password_hash")


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "password_hash" in columns and "hashed_password" not in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("password_hash", new_column_name="hashed_password")
