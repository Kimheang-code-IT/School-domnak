"""Add telegram_key and telegram_chat_id on users.

Revision ID: 0021_user_telegram_key
Revises: 0020_comm_amt_after_discount
Create Date: 2026-07-14
"""

import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0021_user_telegram_key"
down_revision: Union[str, None] = "0020_comm_amt_after_discount"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_key", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("telegram_chat_id", sa.String(length=64), nullable=True))
    op.create_index("ix_users_telegram_key", "users", ["telegram_key"], unique=True)
    op.create_index("ix_users_telegram_chat_id", "users", ["telegram_chat_id"], unique=True)

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM users WHERE telegram_key IS NULL")).fetchall()
    for (user_id,) in rows:
        key = f"LC-{secrets.token_hex(4).upper()}"
        bind.execute(
            sa.text("UPDATE users SET telegram_key = :key WHERE id = :id"),
            {"key": key, "id": user_id},
        )


def downgrade() -> None:
    op.drop_index("ix_users_telegram_chat_id", table_name="users")
    op.drop_index("ix_users_telegram_key", table_name="users")
    op.drop_column("users", "telegram_chat_id")
    op.drop_column("users", "telegram_key")
