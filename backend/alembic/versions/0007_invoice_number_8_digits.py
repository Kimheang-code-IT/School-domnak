"""invoice number 8 digits

Revision ID: 0007_invoice_number_8_digits
Revises: 0006_invoice_number_format
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "0007_invoice_number_8_digits"
down_revision: Union[str, None] = "0006_invoice_number_format"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if "invoices" not in inspect(bind).get_table_names():
        return
    rows = bind.execute(text("SELECT id FROM invoices ORDER BY id")).fetchall()
    for (invoice_id,) in rows:
        bind.execute(
            text("UPDATE invoices SET invoice_no = :invoice_no WHERE id = :id"),
            {"invoice_no": f"DNSS-{int(invoice_id):08d}", "id": invoice_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "invoices" not in inspect(bind).get_table_names():
        return
    rows = bind.execute(text("SELECT id FROM invoices ORDER BY id")).fetchall()
    for (invoice_id,) in rows:
        bind.execute(
            text("UPDATE invoices SET invoice_no = :invoice_no WHERE id = :id"),
            {"invoice_no": f"DNSS-{int(invoice_id):09d}", "id": invoice_id},
        )
