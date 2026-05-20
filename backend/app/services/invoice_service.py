from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
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
from app.services.telegram_activity_service import notify_registration_with_enrollments
from app.utils.enrollment_dates import (
    compute_end_date,
    parse_duration_months,
    prorate_class_price,
    resolve_enrollment_start_date,
)
from app.utils.image_storage import persist_image


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

    stored_image = persist_image(payload.image, "students") if payload.image else None

    if student:
        if stored_image and not student.image:
            student.image = stored_image
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
        image=stored_image,
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
    enroll_start = resolve_enrollment_start_date(payload.start_date, fallback=today)
    created: list[tuple[Enrollment, SchoolClass]] = []
    for school_class in classes.values():
        active = db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.class_id == school_class.id,
                Enrollment.roster_active.is_(True),
            )
        )
        if active:
            active.roster_active = False
            if (active.status or "").strip().lower() == "active":
                active.status = "Completed"
        full_price = Decimal(school_class.full_price or 0)
        out_price = Decimal(school_class.out_price or 0)
        discount = Decimal(school_class.discount_amount or 0)
        class_months = parse_duration_months(school_class.class_duration)
        months = payload.duration_months
        if months is None:
            months = class_months
        if months is not None and months < 0.01:
            months = None
        if months is not None and class_months is not None and months > class_months:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Enrollment duration ({months} months) cannot exceed "
                    f"class duration ({class_months} months)."
                ),
            )
        end_date = compute_end_date(enroll_start, months) if months else None
        prorated_out = (
            prorate_class_price(
                out_price,
                student_months=months,
                class_months=class_months,
            )
            if months and class_months
            else out_price
        )
        prorated_full = (
            prorate_class_price(
                full_price,
                student_months=months,
                class_months=class_months,
            )
            if months and class_months
            else full_price
        )
        prorated_discount = (prorated_full - prorated_out).quantize(Decimal("0.01"))
        enrollment = Enrollment(
            student_id=student.id,
            class_id=school_class.id,
            start_date=enroll_start,
            end_date=end_date,
            register_date=today,
            duration_months=Decimal(str(months)) if months is not None else None,
            total_price=prorated_full,
            discount_price=prorated_discount,
            price_after_discount=prorated_out,
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
    if not class_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No class selected.")

    classes = {
        school_class.id: school_class
        for school_class in db.scalars(
            select(SchoolClass)
            .options(selectinload(SchoolClass.course), selectinload(SchoolClass.teacher))
            .where(SchoolClass.id.in_(class_ids))
        ).all()
    }
    student_months = payload.duration_months
    for class_id in class_ids:
        school_class = classes.get(class_id)
        if not school_class:
            continue
        class_months = parse_duration_months(school_class.class_duration)
        months = student_months if student_months is not None else class_months
        if months is None or months < 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Class \"{school_class.name}\" has no duration; set class duration or enter student months.",
            )
        if class_months is not None and months > class_months:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Enrollment duration ({months} months) cannot exceed "
                    f"class duration ({class_months} months) for \"{school_class.name}\"."
                ),
            )

    invoice_lines: list[InvoiceLineCreate] = []
    subtotal = Decimal("0")
    student, student_is_new = _find_or_create_checkout_student(db, payload)
    for line in payload.lines:
        school_class = classes.get(line.product_id)
        if not school_class:
            continue
        qty = max(1, int(line.qty or 1))
        class_months = parse_duration_months(school_class.class_duration)
        student_months = payload.duration_months or class_months
        base_out = Decimal(school_class.out_price or 0)
        if student_months and class_months:
            price = prorate_class_price(
                base_out,
                student_months=student_months,
                class_months=class_months,
            )
        else:
            price = base_out
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
        if student_is_new or new_enrollments:
            for enrollment, _school_class in new_enrollments:
                db.refresh(enrollment)
            notify_registration_with_enrollments(
                student,
                new_enrollments,
                is_new_student=student_is_new,
                registered_by=username,
                invoice=persisted,
            )
    return InvoiceCheckoutResponse(
        invoice_no=invoice.invoice_no,
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        total=invoice.total,
        invoice=invoice,
    )
