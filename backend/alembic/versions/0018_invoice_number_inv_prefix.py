"""Rename invoice numbers to INV-0000001 format.

Revision ID: 0018_invoice_number_inv_prefix
Revises: 0017_normalize_relationships
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0018_invoice_number_inv_prefix"
down_revision: Union[str, None] = "0017_normalize_relationships"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(text("SELECT id FROM invoices ORDER BY id")).fetchall()
    for (invoice_id,) in rows:
        bind.execute(
            text("UPDATE invoices SET invoice_no = :invoice_no WHERE id = :id"),
            {"invoice_no": f"INV-{int(invoice_id):07d}", "id": invoice_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(text("SELECT id FROM invoices ORDER BY id")).fetchall()
    for (invoice_id,) in rows:
        bind.execute(
            text("UPDATE invoices SET invoice_no = :invoice_no WHERE id = :id"),
            {"invoice_no": f"DNS-{int(invoice_id):07d}", "id": invoice_id},
        )
