"""role permissions

Revision ID: 0002_role_permissions
Revises: 0001_init
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision: str = "0002_role_permissions"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("roles")}
    if "permissions" not in columns:
        op.add_column("roles", sa.Column("permissions", sa.JSON(), nullable=True))
        bind.execute(text("UPDATE roles SET permissions = '{}' WHERE permissions IS NULL"))
    if "page_access" in columns:
        with op.batch_alter_table("roles") as batch_op:
            batch_op.drop_column("page_access")


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("roles")}
    if "permissions" in columns:
        with op.batch_alter_table("roles") as batch_op:
            batch_op.drop_column("permissions")
    if "page_access" not in columns:
        op.add_column("roles", sa.Column("page_access", sa.JSON(), nullable=True))
