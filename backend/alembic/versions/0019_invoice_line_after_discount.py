"""Store invoice line totals as grand total after discount.

Revision ID: 0019_invoice_line_after_discount
Revises: 0018_invoice_number_inv_prefix
Create Date: 2026-07-14
"""

from decimal import Decimal
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0019_invoice_line_after_discount"
down_revision: Union[str, None] = "0018_invoice_number_inv_prefix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    invoices = bind.execute(
        text(
            """
            SELECT id, subtotal, discount_amount, total
            FROM invoices
            WHERE COALESCE(discount_amount, 0) > 0
            ORDER BY id
            """
        )
    ).fetchall()

    for invoice_id, subtotal, discount_amount, invoice_total in invoices:
        subtotal_d = Decimal(str(subtotal or 0))
        total_d = Decimal(str(invoice_total or 0))
        if subtotal_d <= 0:
            continue
        lines = bind.execute(
            text(
                """
                SELECT id, qty, total
                FROM invoice_lines
                WHERE invoice_id = :invoice_id
                ORDER BY id
                """
            ),
            {"invoice_id": invoice_id},
        ).fetchall()
        if not lines:
            continue

        allocated = Decimal("0")
        for index, (line_id, qty, line_total) in enumerate(lines):
            base = Decimal(str(line_total or 0))
            if index == len(lines) - 1:
                new_total = (total_d - allocated).quantize(Decimal("0.01"))
            else:
                new_total = (base / subtotal_d * total_d).quantize(Decimal("0.01"))
                allocated += new_total
            qty_d = Decimal(str(qty or 1)) or Decimal("1")
            new_price = (new_total / qty_d).quantize(Decimal("0.01"))
            bind.execute(
                text(
                    """
                    UPDATE invoice_lines
                    SET price = :price, total = :total
                    WHERE id = :id
                    """
                ),
                {"price": str(new_price), "total": str(new_total), "id": line_id},
            )

    # Commission amount alignment (including null invoice_id) is in 0020_comm_amt_after_discount.

    # Refresh finance.amount from discounted line totals and final_price.
    finance_rows = bind.execute(
        text("SELECT id, class_id, electricity, water, internet, total_commission, facebook, other FROM finance WHERE class_id IS NOT NULL")
    ).fetchall()
    for fin_id, class_id, elec, water, inet, total_comm, facebook, other in finance_rows:
        amount = bind.execute(
            text("SELECT COALESCE(SUM(total), 0) FROM invoice_lines WHERE class_id = :class_id"),
            {"class_id": class_id},
        ).scalar()
        amount_d = Decimal(str(amount or 0))
        costs = (
            Decimal(str(elec or 0))
            + Decimal(str(water or 0))
            + Decimal(str(inet or 0))
            + Decimal(str(total_comm or 0))
            + Decimal(str(facebook or 0))
            + Decimal(str(other or 0))
        )
        # Also refresh total_commission from commission rows.
        total_comm_sum = bind.execute(
            text("SELECT COALESCE(SUM(commission), 0) FROM commissions WHERE class_id = :class_id"),
            {"class_id": class_id},
        ).scalar()
        total_comm_d = Decimal(str(total_comm_sum or 0))
        costs = (
            Decimal(str(elec or 0))
            + Decimal(str(water or 0))
            + Decimal(str(inet or 0))
            + total_comm_d
            + Decimal(str(facebook or 0))
            + Decimal(str(other or 0))
        )
        bind.execute(
            text(
                """
                UPDATE finance
                SET amount = :amount,
                    total_commission = :total_commission,
                    final_price = :final_price
                WHERE id = :id
                """
            ),
            {
                "amount": str(amount_d),
                "total_commission": str(total_comm_d),
                "final_price": str(amount_d - costs),
                "id": fin_id,
            },
        )


def downgrade() -> None:
    # Cannot safely restore pre-discount line totals without stored originals.
    pass
