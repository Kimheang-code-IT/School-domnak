"""Add invoice payment method and paid/own amounts.

Revision ID: 0022_invoice_payment_own
Revises: 0021_user_telegram_key
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0022_invoice_payment_own"
down_revision: Union[str, None] = "0021_user_telegram_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("payment_method", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "invoices",
        sa.Column("amount_own", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    # Existing invoices are treated as fully paid.
    op.execute(
        sa.text(
            "UPDATE invoices SET payment_method = COALESCE(payment_method, 'cash'), "
            "amount_paid = total, amount_own = 0"
        )
    )


def downgrade() -> None:
    op.drop_column("invoices", "amount_own")
    op.drop_column("invoices", "amount_paid")
    op.drop_column("invoices", "payment_method")
