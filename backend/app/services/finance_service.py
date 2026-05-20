from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.class_model import SchoolClass
from app.models.commission import Commission
from app.models.finance import Finance


def recalculate_finance(row: Finance) -> None:
    costs = row.electricity + row.water + row.internet + row.total_commission + row.facebook + row.other
    row.final_price = Decimal(row.amount or 0) - Decimal(costs or 0)


def ensure_finance_for_class(db: Session, school_class: SchoolClass) -> Finance:
    amount = Decimal(school_class.out_price or 0)
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
            amount=amount,
            in_price_for_pos=amount,
        )
        db.add(row)
    else:
        row.amount = amount
        row.in_price_for_pos = amount
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
    recalculate_finance(row)


def sync_finance_for_all_classes(db: Session) -> int:
    """Create finance rows for classes that do not have one yet."""
    existing_ids = {
        class_id
        for class_id in db.scalars(select(Finance.class_id).where(Finance.class_id.isnot(None))).all()
        if class_id is not None
    }
    statement = select(SchoolClass)
    if existing_ids:
        statement = statement.where(SchoolClass.id.notin_(existing_ids))
    missing = db.scalars(statement).all()
    for school_class in missing:
        ensure_finance_for_class(db, school_class)
    return len(missing)
