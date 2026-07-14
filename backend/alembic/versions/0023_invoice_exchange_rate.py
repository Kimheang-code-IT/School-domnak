"""Add exchange_rate on invoices for KHR display.

Revision ID: 0023_invoice_exchange_rate
Revises: 0022_invoice_payment_own
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0023_invoice_exchange_rate"
down_revision: Union[str, None] = "0022_invoice_payment_own"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("exchange_rate", sa.Numeric(12, 2), nullable=False, server_default="4100"),
    )


def downgrade() -> None:
    op.drop_column("invoices", "exchange_rate")
