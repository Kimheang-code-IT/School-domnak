from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.class_model import SchoolClass
from app.models.commission import Commission
from app.models.finance import Finance
from app.models.invoice import InvoiceLine


def recalculate_finance(row: Finance) -> None:
    costs = row.electricity + row.water + row.internet + row.total_commission + row.facebook + row.other
    row.final_price = Decimal(row.amount or 0) - Decimal(costs or 0)


def _class_grand_total_after_discount(db: Session, class_id: int) -> Decimal:
    """Sum of invoice line totals for the class (student payments / grand total after discount)."""
    total = db.scalar(
        select(func.coalesce(func.sum(InvoiceLine.total), 0)).where(InvoiceLine.class_id == class_id)
    )
    return Decimal(total or 0)


def ensure_finance_for_class(db: Session, school_class: SchoolClass) -> Finance:
    catalog_price = Decimal(school_class.out_price or 0)
    sale_total = _class_grand_total_after_discount(db, school_class.id)
    row = db.scalar(select(Finance).where(Finance.class_id == school_class.id))
    if row is None:
        row = Finance(
            class_id=school_class.id,
            electricity=Decimal("0"),
            water=Decimal("0"),
            internet=Decimal("0"),
            total_commission=Decimal("0"),
            facebook=Decimal("0"),
            other=Decimal("0"),
            amount=sale_total,
            in_price_for_pos=catalog_price,
        )
        db.add(row)
    else:
        row.amount = sale_total
        row.in_price_for_pos = catalog_price
    recalculate_finance(row)
    db.flush()
    return row


def refresh_finance_total_commission(db: Session, class_id: int) -> None:
    row = db.scalar(select(Finance).where(Finance.class_id == class_id))
    if row is None:
        return
    total = db.scalar(
        select(func.coalesce(func.sum(Commission.commission), 0)).where(Commission.class_id == class_id)
    ) or Decimal("0")
    row.total_commission = Decimal(total)
    row.amount = _class_grand_total_after_discount(db, class_id)
    recalculate_finance(row)


def sync_finance_for_all_classes(db: Session) -> int:
    """Ensure every class has a finance row and amounts match invoice grand totals."""
    classes = db.scalars(select(SchoolClass)).all()
    for school_class in classes:
        ensure_finance_for_class(db, school_class)
    return len(classes)


def refresh_all_finance_sale_totals(db: Session) -> int:
    """Recompute finance.amount from invoice line grand totals for existing rows."""
    rows = db.scalars(select(Finance).where(Finance.class_id.isnot(None))).all()
    for row in rows:
        if row.class_id is None:
            continue
        row.amount = _class_grand_total_after_discount(db, row.class_id)
        recalculate_finance(row)
    if rows:
        db.flush()
    return len(rows)
