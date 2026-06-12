from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.models.class_model import SchoolClass
from app.models.enrollment import Enrollment
from app.models.invoice import Invoice, InvoiceLine
from app.models.student import Student
from app.schemas.invoice import (
    InvoiceCheckoutCreate,
    InvoiceCheckoutResponse,
    InvoiceCreate,
    InvoiceLineCreate,
    InvoiceLineRead,
    InvoiceProduct,
    InvoiceRead,
)
from app.services.audit_service import write_audit_log
from app.services.commission_service import record_commissions_for_invoice
from app.services.telegram_activity_service import notify_class_enrollment
from app.utils.task_dispatch import dispatch_new_student_alerts
from app.utils.enrollment_dates import compute_end_date, parse_duration_months


def format_invoice_no(sequence: int) -> str:
    return f"DNSS-{sequence:08d}"


def get_next_invoice_no(db: Session) -> str:
    next_invoice_id = (db.scalar(select(Invoice.id).order_by(Invoice.id.desc())) or 0) + 1
    return format_invoice_no(next_invoice_id)


def _to_read(invoice: Invoice) -> InvoiceRead:
    return InvoiceRead(
        id=invoice.id,
        invoice_no=invoice.invoice_no,
        student_id=invoice.student_id,
        student_name=invoice.student_name,
        student_phone=invoice.student_phone,
        address=invoice.address,
        seller=invoice.seller,
        source=invoice.source,
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        total=invoice.total,
        created_at=invoice.created_at,
        lines=[
            InvoiceLineRead(
                id=line.id,
                product=InvoiceProduct(name=line.product_name, out_price=line.price),
                product_name=line.product_name,
                qty=line.qty,
                price=line.price,
                total=line.total,
            )
            for line in invoice.lines
        ],
    )


def get_invoice(db: Session, invoice_id: int) -> InvoiceRead | None:
    invoice = db.scalar(
        select(Invoice).options(selectinload(Invoice.lines)).where(Invoice.id == invoice_id)
    )
    return _to_read(invoice) if invoice else None


def _clean(value: str | None) -> str:
    return str(value or "").strip()


def _find_or_create_checkout_student(db: Session, payload: InvoiceCheckoutCreate) -> tuple[Student, bool]:
    student = db.get(Student, payload.student_id) if payload.student_id else None
    is_new = False
    phone = _clean(payload.customer_phone)
    name_km = _clean(payload.name_km)
    name_en = _clean(payload.name_en)
    customer_name = _clean(payload.customer_name)

    if not student and phone:
        student = db.scalar(select(Student).where(Student.phone == phone).order_by(Student.id))

    if not student and (name_km or name_en or customer_name):
        statement = select(Student).order_by(Student.id)
        if name_km and name_en:
            statement = statement.where(Student.name_km == name_km, Student.name_en == name_en)
        elif name_en or customer_name:
            statement = statement.where(Student.name_en == (name_en or customer_name))
        else:
            statement = statement.where(Student.name_km == name_km)
        student = db.scalar(statement)

    if student:
        if payload.image and not student.image:
            student.image = payload.image
        if payload.gender and not student.gender:
            student.gender = payload.gender
        if payload.birthdate and not student.birthdate:
            student.birthdate = payload.birthdate
        if payload.province and not student.province:
            student.province = payload.province
        if phone and not student.phone:
            student.phone = phone
        db.flush()
        return student, False

    fallback_name = customer_name or name_en or name_km or "Student"
    is_new = True
    student = Student(
        image=payload.image,
        name_km=name_km or fallback_name,
        name_en=name_en or fallback_name,
        gender=payload.gender,
        birthdate=payload.birthdate,
        phone=phone or None,
        province=payload.province,
    )
    db.add(student)
    db.flush()
    db.refresh(student)
    return student, is_new


def _ensure_checkout_enrollments(
    db: Session,
    *,
    student: Student,
    classes: dict[int, SchoolClass],
    payload: InvoiceCheckoutCreate,
) -> list[tuple[Enrollment, SchoolClass]]:
    today = date.today()
    created: list[tuple[Enrollment, SchoolClass]] = []
    for school_class in classes.values():
        existing = db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.class_id == school_class.id,
                Enrollment.roster_active.is_(True),
            )
        )
        if existing:
            continue
        full_price = Decimal(school_class.full_price or 0)
        out_price = Decimal(school_class.out_price or 0)
        discount = Decimal(school_class.discount_amount or 0)
        months = parse_duration_months(school_class.class_duration)
        end_date = compute_end_date(today, months) if months else None
        enrollment = Enrollment(
            student_id=student.id,
            class_id=school_class.id,
            start_date=today,
            end_date=end_date,
            register_date=today,
            total_price=full_price,
            discount_price=discount,
            price_after_discount=out_price,
            status="Active",
            roster_active=True,
        )
        db.add(enrollment)
        created.append((enrollment, school_class))
    db.flush()
    return created


def create_invoice(db: Session, payload: InvoiceCreate, *, username: str = "system") -> InvoiceRead:
    subtotal = sum((line.price * line.qty for line in payload.lines), Decimal("0"))
    total = subtotal - payload.discount_amount
    invoice = Invoice(
        invoice_no=get_next_invoice_no(db),
        student_id=payload.student_id,
        student_name=payload.student_name,
        student_phone=payload.student_phone,
        address=payload.address,
        seller=payload.seller,
        source=payload.source,
        subtotal=subtotal,
        discount_amount=payload.discount_amount,
        total=total,
    )
    for line in payload.lines:
        invoice.lines.append(
            InvoiceLine(
                class_id=line.class_id,
                product_name=line.product_name,
                qty=line.qty,
                price=line.price,
                total=line.price * line.qty,
            )
        )
    db.add(invoice)
    db.flush()
    db.refresh(invoice)
    write_audit_log(db, action="Create", username=username, description=f"Created invoice {invoice.invoice_no}")
    db.commit()
    return get_invoice(db, invoice.id)  # type: ignore[return-value]


def checkout_invoice(db: Session, payload: InvoiceCheckoutCreate, *, username: str = "system") -> InvoiceCheckoutResponse:
    class_ids = [line.product_id for line in payload.lines]
    classes = {
        school_class.id: school_class
        for school_class in db.scalars(
            select(SchoolClass)
            .options(selectinload(SchoolClass.course), selectinload(SchoolClass.teacher))
            .where(SchoolClass.id.in_(class_ids))
        ).all()
    }
    invoice_lines: list[InvoiceLineCreate] = []
    subtotal = Decimal("0")
    student, student_is_new = _find_or_create_checkout_student(db, payload)
    for line in payload.lines:
        school_class = classes.get(line.product_id)
        if not school_class:
            continue
        qty = max(1, int(line.qty or 1))
        price = Decimal(school_class.out_price or 0)
        subtotal += price * qty
        invoice_lines.append(
            InvoiceLineCreate(
                class_id=school_class.id,
                product_name=school_class.name,
                qty=qty,
                price=price,
            )
        )

    new_enrollments = _ensure_checkout_enrollments(db, student=student, classes=classes, payload=payload)

    discount_percent = max(Decimal("0"), min(Decimal(payload.discount_percent or 0), Decimal("100")))
    discount_amount = subtotal * discount_percent / Decimal("100")
    invoice = create_invoice(
        db,
        InvoiceCreate(
            student_id=student.id,
            student_name=payload.customer_name,
            student_phone=payload.customer_phone,
            address=(payload.customer_address or "").strip() or (payload.province or "").strip() or None,
            seller=username,
            source=payload.source,
            discount_amount=discount_amount,
            lines=invoice_lines,
        ),
        username=username,
    )
    persisted = db.scalar(
        select(Invoice).options(selectinload(Invoice.lines)).where(Invoice.id == invoice.id)
    )
    if persisted is not None:
        record_commissions_for_invoice(
            db,
            persisted,
            classes,
            source=payload.source,
        )
        db.commit()
        if student_is_new:
            dispatch_new_student_alerts(student.id, registered_by=username)
        for enrollment, school_class in new_enrollments:
            db.refresh(enrollment)
            notify_class_enrollment(student, school_class, enrollment, enrolled_by=username)
    return InvoiceCheckoutResponse(
        invoice_no=invoice.invoice_no,
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        total=invoice.total,
        invoice=invoice,
    )
