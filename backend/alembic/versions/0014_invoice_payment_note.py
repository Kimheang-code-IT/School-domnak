"""Add optional payment_note on invoices.

Revision ID: 0014_invoice_payment_note
Revises: 0013_performance_indexes
Create Date: 2026-07-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_invoice_payment_note"
down_revision: Union[str, None] = "0013_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("payment_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "payment_note")
