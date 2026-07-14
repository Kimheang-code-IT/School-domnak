"""Align commission sale amounts with discounted invoice lines.

Revision ID: 0020_comm_amt_after_discount
Revises: 0019_invoice_line_after_discount
Create Date: 2026-07-14
"""

from decimal import Decimal
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0020_comm_amt_after_discount"
down_revision: Union[str, None] = "0019_invoice_line_after_discount"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _recalc_commission(mode, fixed, percent, sale: Decimal) -> Decimal:
    mode_l = (mode or "usd").strip().lower()
    if mode_l == "percent":
        pct = Decimal(str(percent or 0))
        return (sale * pct / Decimal("100")).quantize(Decimal("0.01")) if pct > 0 else Decimal("0")
    return Decimal(str(fixed or 0)).quantize(Decimal("0.01"))


def upgrade() -> None:
    bind = op.get_bind()

    with_invoice = bind.execute(
        text(
            """
            SELECT c.id, c.class_id, c.invoice_id,
                   sc.teacher_commission_mode, sc.teacher_commission, sc.teacher_commission_percent
            FROM commissions c
            LEFT JOIN classes sc ON sc.id = c.class_id
            WHERE c.invoice_id IS NOT NULL AND c.class_id IS NOT NULL
            """
        )
    ).fetchall()
    for commission_id, class_id, invoice_id, mode, fixed, percent in with_invoice:
        line_total = bind.execute(
            text(
                """
                SELECT COALESCE(SUM(total), 0)
                FROM invoice_lines
                WHERE invoice_id = :invoice_id AND class_id = :class_id
                """
            ),
            {"invoice_id": invoice_id, "class_id": class_id},
        ).scalar()
        sale = Decimal(str(line_total or 0)).quantize(Decimal("0.01"))
        commission_amt = _recalc_commission(mode, fixed, percent, sale)
        bind.execute(
            text("UPDATE commissions SET amount = :amount, commission = :commission WHERE id = :id"),
            {"amount": str(sale), "commission": str(commission_amt), "id": commission_id},
        )

    orphans = bind.execute(
        text(
            """
            SELECT c.id, c.class_id, c.student_id,
                   sc.teacher_commission_mode, sc.teacher_commission, sc.teacher_commission_percent
            FROM commissions c
            LEFT JOIN classes sc ON sc.id = c.class_id
            WHERE c.invoice_id IS NULL AND c.class_id IS NOT NULL AND c.student_id IS NOT NULL
            """
        )
    ).fetchall()
    for commission_id, class_id, student_id, mode, fixed, percent in orphans:
        match = bind.execute(
            text(
                """
                SELECT i.id, COALESCE(SUM(l.total), 0) AS line_total
                FROM invoices i
                JOIN invoice_lines l ON l.invoice_id = i.id
                WHERE i.student_id = :student_id AND l.class_id = :class_id
                GROUP BY i.id
                ORDER BY i.id DESC
                LIMIT 1
                """
            ),
            {"student_id": student_id, "class_id": class_id},
        ).fetchone()
        if not match:
            continue
        invoice_id, line_total = match
        sale = Decimal(str(line_total or 0)).quantize(Decimal("0.01"))
        commission_amt = _recalc_commission(mode, fixed, percent, sale)
        bind.execute(
            text(
                """
                UPDATE commissions
                SET invoice_id = :invoice_id, amount = :amount, commission = :commission
                WHERE id = :id
                """
            ),
            {
                "invoice_id": invoice_id,
                "amount": str(sale),
                "commission": str(commission_amt),
                "id": commission_id,
            },
        )

    finance_rows = bind.execute(
        text(
            """
            SELECT id, class_id, electricity, water, internet, facebook, other, amount
            FROM finance
            WHERE class_id IS NOT NULL
            """
        )
    ).fetchall()
    for fin_id, class_id, elec, water, inet, facebook, other, amount in finance_rows:
        total_comm = Decimal(
            str(
                bind.execute(
                    text("SELECT COALESCE(SUM(commission), 0) FROM commissions WHERE class_id = :class_id"),
                    {"class_id": class_id},
                ).scalar()
                or 0
            )
        )
        amount_d = Decimal(str(amount or 0))
        costs = (
            Decimal(str(elec or 0))
            + Decimal(str(water or 0))
            + Decimal(str(inet or 0))
            + total_comm
            + Decimal(str(facebook or 0))
            + Decimal(str(other or 0))
        )
        bind.execute(
            text(
                """
                UPDATE finance
                SET total_commission = :total_commission, final_price = :final_price
                WHERE id = :id
                """
            ),
            {
                "total_commission": str(total_comm),
                "final_price": str(amount_d - costs),
                "id": fin_id,
            },
        )


def downgrade() -> None:
    pass
