from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_model import SchoolClass
from app.models.commission import Commission
from app.models.invoice import Invoice, InvoiceLine
from app.models.student import Student
from app.services.finance_service import ensure_finance_for_class, refresh_finance_total_commission


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
    student: Student | None,
    invoice: Invoice | None,
    amount: Decimal,
) -> Commission:
    sale_amount = Decimal(amount or 0)
    commission_amount = _commission_amount(school_class, sale_amount)
    teacher_id = school_class.teacher_id
    if teacher_id is None and getattr(school_class, "teacher", None) is not None:
        teacher_id = school_class.teacher.id
    row = Commission(
        class_id=school_class.id,
        student_id=student.id if student else None,
        invoice_id=invoice.id if invoice else None,
        teacher_id=teacher_id,
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
) -> None:
    student = invoice.student
    if student is None and invoice.student_id:
        student = db.get(Student, invoice.student_id)
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
            student=student,
            invoice=invoice,
            amount=line_total,
        )


def sync_commissions_from_invoices(db: Session) -> int:
    """Backfill commission rows from existing invoice lines (idempotent-ish)."""
    statement = (
        select(InvoiceLine, Invoice, SchoolClass, Student)
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .outerjoin(SchoolClass, SchoolClass.id == InvoiceLine.class_id)
        .outerjoin(Student, Student.id == Invoice.student_id)
        .where(InvoiceLine.class_id.isnot(None))
    )
    created = 0
    for line, invoice, school_class, student in db.execute(statement).all():
        if school_class is None:
            continue
        amount = Decimal(line.total or 0)
        if amount <= 0:
            continue
        exists = db.scalar(
            select(Commission.id)
            .where(
                Commission.class_id == line.class_id,
                Commission.invoice_id == invoice.id,
                Commission.student_id == invoice.student_id,
                Commission.amount == amount,
            )
            .limit(1)
        )
        if exists:
            continue
        record_commission_for_sale(
            db,
            school_class=school_class,
            student=student,
            invoice=invoice,
            amount=amount,
        )
        created += 1
    if created:
        db.flush()
    return created
