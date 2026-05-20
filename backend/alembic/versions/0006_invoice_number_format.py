"""invoice number format

Revision ID: 0006_invoice_number_format
Revises: 0005_remove_course_extra_fields
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "0006_invoice_number_format"
down_revision: Union[str, None] = "0005_remove_course_extra_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if "invoices" not in inspect(bind).get_table_names():
        return
    rows = bind.execute(text("SELECT id, invoice_no FROM invoices WHERE invoice_no NOT LIKE 'DNSS-%' ORDER BY id")).fetchall()
    for invoice_id, _invoice_no in rows:
        bind.execute(
            text("UPDATE invoices SET invoice_no = :invoice_no WHERE id = :id"),
            {"invoice_no": f"DNSS-{int(invoice_id):09d}", "id": invoice_id},
        )


def downgrade() -> None:
    pass
