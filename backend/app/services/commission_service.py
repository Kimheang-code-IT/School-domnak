from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.class_model import SchoolClass
from app.models.commission import Commission
from app.models.finance import Finance
from app.models.invoice import Invoice, InvoiceLine
from app.services.finance_service import ensure_finance_for_class, refresh_finance_total_commission


def _english_student_name(invoice: Invoice) -> str:
    raw = (invoice.student_name or "").strip()
    if not raw:
        return "—"
    if " · " in raw:
        parts = [part.strip() for part in raw.split(" · ") if part.strip()]
        if len(parts) >= 2:
            return parts[-1]
    return raw


def _commission_amount(school_class: SchoolClass, sale_amount: Decimal) -> Decimal:
    """Teacher commission from class: fixed USD or % of each payment line."""
    mode = (school_class.teacher_commission_mode or "usd").strip().lower()
    if mode == "percent":
        pct = Decimal(school_class.teacher_commission_percent or 0)
        if pct <= 0:
            return Decimal("0")
        return (sale_amount * pct / Decimal("100")).quantize(Decimal("0.01"))
    return Decimal(school_class.teacher_commission or 0).quantize(Decimal("0.01"))


def record_commission_for_sale(
    db: Session,
    *,
    school_class: SchoolClass,
    student_name: str,
    source: str | None,
    amount: Decimal,
) -> Commission:
    sale_amount = Decimal(amount or 0)
    commission_amount = _commission_amount(school_class, sale_amount)
    teacher_name = (school_class.teacher_name or "Unknown").strip() or "Unknown"
    row = Commission(
        class_id=school_class.id,
        class_name=school_class.name,
        student_name=student_name or "—",
        teacher_name=teacher_name,
        source=(source or "").strip() or None,
        amount=sale_amount,
        commission=commission_amount,
    )
    db.add(row)
    db.flush()
    if school_class.id is not None:
        ensure_finance_for_class(db, school_class)
        refresh_finance_total_commission(db, school_class.id)
    return row


def record_commissions_for_invoice(
    db: Session,
    invoice: Invoice,
    classes_by_id: dict[int, SchoolClass],
    *,
    source: str | None,
) -> None:
    student_name = _english_student_name(invoice)
    for line in invoice.lines:
        if line.class_id is None:
            continue
        school_class = classes_by_id.get(line.class_id)
        if not school_class:
            school_class = db.get(SchoolClass, line.class_id)
        if not school_class:
            continue
        line_total = Decimal(line.total or 0)
        if line_total <= 0:
            continue
        record_commission_for_sale(
            db,
            school_class=school_class,
            student_name=student_name,
            source=source,
            amount=line_total,
        )


def sync_commissions_from_invoices(db: Session) -> int:
    """Backfill commission rows from existing invoice lines (idempotent-ish)."""
    statement = (
        select(InvoiceLine, Invoice, SchoolClass)
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .outerjoin(SchoolClass, SchoolClass.id == InvoiceLine.class_id)
        .where(InvoiceLine.class_id.isnot(None))
    )
    created = 0
    for line, invoice, school_class in db.execute(statement).all():
        if school_class is None:
            continue
        student_name = _english_student_name(invoice)
        amount = Decimal(line.total or 0)
        if amount <= 0:
            continue
        exists = db.scalar(
            select(Commission.id)
            .where(
                Commission.class_id == line.class_id,
                Commission.student_name == student_name,
                Commission.amount == amount,
            )
            .limit(1)
        )
        if exists:
            continue
        record_commission_for_sale(
            db,
            school_class=school_class,
            student_name=student_name,
            source=invoice.source,
            amount=amount,
        )
        created += 1
    if created:
        db.flush()
    return created
