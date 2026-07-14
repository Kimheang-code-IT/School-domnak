"""Drop unused source columns from invoices and commissions.

Revision ID: 0015_drop_source_columns
Revises: 0014_invoice_payment_note
Create Date: 2026-07-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_drop_source_columns"
down_revision: Union[str, None] = "0014_invoice_payment_note"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("invoices", "source")
    op.drop_column("commissions", "source")


def downgrade() -> None:
    op.add_column("commissions", sa.Column("source", sa.String(length=100), nullable=True))
    op.add_column("invoices", sa.Column("source", sa.String(length=100), nullable=True))
