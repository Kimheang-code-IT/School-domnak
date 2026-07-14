from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.class_model import SchoolClass
from app.models.commission import Commission
from app.models.enrollment import Enrollment
from app.models.invoice import Invoice, InvoiceLine
from app.models.student import Student
from app.schemas.invoice import (
    InvoiceCheckoutCreate,
    InvoiceCheckoutResponse,
    InvoiceCreate,
    InvoiceLineCreate,
    InvoiceLineRead,
    InvoicePayOwn,
    InvoiceProduct,
    InvoiceRead,
    InvoiceUpdate,
)
from app.services.audit_service import write_audit_log
from app.services.commission_service import record_commissions_for_invoice
from app.services.finance_service import ensure_finance_for_class, refresh_finance_total_commission
from app.utils.task_dispatch import dispatch_checkout_post_process
from app.utils.enrollment_dates import (
    compute_end_date,
    parse_duration_months,
    prorate_class_price,
    resolve_enrollment_start_date,
)
from app.utils.image_storage import persist_image


def format_invoice_no(sequence: int) -> str:
    return f"INV-{sequence:07d}"


def get_next_invoice_no(db: Session) -> str:
    """Allocate next invoice number with transaction-scoped lock (PostgreSQL)."""
    from sqlalchemy import func, text

    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(42424242)"))
    latest_id = db.scalar(select(func.max(Invoice.id))) or 0
    return format_invoice_no(latest_id + 1)


def _student_display_name(student: Student | None) -> str | None:
    if not student:
        return None
    parts = [part for part in [(student.name_km or "").strip(), (student.name_en or "").strip()] if part]
    if parts:
        return " · ".join(parts)
    return None


def _line_class_name(line: InvoiceLine) -> str:
    if line.school_class is not None:
        return line.school_class.name
    return "—"


def _normalize_payment_method(raw: str | None) -> str:
    value = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "cash": "cash",
        "bank": "bank",
        "bank_transfer": "bank",
        "aba": "bank",
        "aba_bank": "bank",
        "wing": "wing",
        "own": "own",
        "other": "other",
    }
    return aliases.get(value, "cash")


def _money(value: Decimal | float | int | None) -> Decimal:
    try:
        amount = Decimal(str(value if value is not None else 0))
    except Exception:
        amount = Decimal("0")
    if amount < 0:
        amount = Decimal("0")
    return amount.quantize(Decimal("0.01"))


def _resolve_payment_amounts(
    *,
    total: Decimal,
    payment_method: str | None,
    amount_paid: Decimal | float | int | None = None,
    amount_own: Decimal | float | int | None = None,
) -> tuple[str, Decimal, Decimal, str]:
    method = _normalize_payment_method(payment_method)
    total_q = _money(total)
    if method != "own":
        return method, total_q, Decimal("0.00"), "paid"

    paid = _money(amount_paid)
    own = _money(amount_own)
    if amount_paid is None and amount_own is None:
        paid = Decimal("0.00")
        own = total_q
    elif amount_paid is None:
        paid = max(Decimal("0.00"), (total_q - own).quantize(Decimal("0.01")))
    elif amount_own is None:
        own = max(Decimal("0.00"), (total_q - paid).quantize(Decimal("0.01")))

    if paid > total_q:
        paid = total_q
    own = (total_q - paid).quantize(Decimal("0.01"))

    if own <= 0:
        return "cash", total_q, Decimal("0.00"), "paid"
    return "own", paid, own, "own"


def _payment_status_from_amounts(amount_own: Decimal | None) -> str:
    return "own" if _money(amount_own) > 0 else "paid"


def _exchange_rate(value: Decimal | float | int | None) -> Decimal:
    try:
        rate = Decimal(str(value if value is not None else 4100))
    except Exception:
        rate = Decimal("4100")
    if rate <= 0:
        rate = Decimal("4100")
    return rate.quantize(Decimal("0.01"))


def _to_read(invoice: Invoice) -> InvoiceRead:
    student = invoice.student
    amount_paid = _money(getattr(invoice, "amount_paid", None))
    amount_own = _money(getattr(invoice, "amount_own", None))
    payment_method = _normalize_payment_method(getattr(invoice, "payment_method", None))
    if amount_own > 0:
        payment_method = "own"
    return InvoiceRead(
        id=invoice.id,
        invoice_no=invoice.invoice_no,
        student_id=invoice.student_id,
        student_name=_student_display_name(student),
        name_km=(student.name_km if student else None),
        name_en=(student.name_en if student else None),
        student_phone=(student.phone if student else None),
        gender=(student.gender if student else None),
        birthdate=(student.birthdate if student else None),
        address=invoice.address,
        seller=invoice.seller,
        payment_note=invoice.payment_note,
        payment_method=payment_method,
        amount_paid=amount_paid,
        amount_own=amount_own,
        exchange_rate=_exchange_rate(getattr(invoice, "exchange_rate", None)),
        payment_status=_payment_status_from_amounts(amount_own),
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        total=invoice.total,
        created_at=invoice.created_at,
        lines=[
            InvoiceLineRead(
                id=line.id,
                class_id=line.class_id,
                product=InvoiceProduct(name=_line_class_name(line), out_price=line.price),
                product_name=_line_class_name(line),
                qty=line.qty,
                price=line.price,
                total=line.total,
            )
            for line in invoice.lines
        ],
    )


def _invoice_load_options():
    return (
        selectinload(Invoice.lines).selectinload(InvoiceLine.school_class),
        selectinload(Invoice.student),
    )


def get_invoice(db: Session, invoice_id: int) -> InvoiceRead | None:
    invoice = db.scalar(
        select(Invoice).options(*_invoice_load_options()).where(Invoice.id == invoice_id)
    )
    return _to_read(invoice) if invoice else None


def get_invoice_by_no(db: Session, invoice_no: str) -> InvoiceRead | None:
    cleaned = (invoice_no or "").strip()
    if not cleaned:
        return None
    invoice = db.scalar(
        select(Invoice).options(*_invoice_load_options()).where(Invoice.invoice_no == cleaned)
    )
    return _to_read(invoice) if invoice else None


def _allocate_discounted_lines(
    lines: list[InvoiceLineCreate],
    *,
    discount_amount: Decimal,
) -> tuple[Decimal, Decimal, Decimal, list[tuple[int, int, Decimal, Decimal]]]:
    """Return subtotal, discount, total, and (class_id, qty, unit_price, line_total) rows."""
    if not lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No invoice lines.")
    for line in lines:
        if not line.class_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each line requires classId.")

    subtotal = sum((Decimal(line.price) * Decimal(line.qty or 1) for line in lines), Decimal("0"))
    discount = Decimal(discount_amount or 0)
    if discount < 0:
        discount = Decimal("0")
    if discount > subtotal:
        discount = subtotal
    total = (subtotal - discount).quantize(Decimal("0.01"))

    line_bases = [Decimal(line.price) * Decimal(line.qty or 1) for line in lines]
    allocated = Decimal("0")
    built: list[tuple[int, int, Decimal, Decimal]] = []
    for index, line in enumerate(lines):
        base = line_bases[index]
        if index == len(lines) - 1:
            line_total = (total - allocated).quantize(Decimal("0.01"))
        elif subtotal > 0:
            line_total = (base / subtotal * total).quantize(Decimal("0.01"))
            allocated += line_total
        else:
            line_total = Decimal("0")
        qty = max(1, int(line.qty or 1))
        unit_price = (line_total / Decimal(qty)).quantize(Decimal("0.01")) if qty else line_total
        built.append((int(line.class_id), qty, unit_price, line_total))
    return subtotal, discount, total, built


def _create_active_enrollment(
    db: Session,
    *,
    student: Student,
    school_class: SchoolClass,
    duration_months: float | None = None,
    start_date: date | None = None,
) -> Enrollment:
    today = date.today()
    enroll_start = resolve_enrollment_start_date(start_date, fallback=today)
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
    class_months = parse_duration_months(school_class.class_duration)
    months = duration_months if duration_months is not None else class_months
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
        prorate_class_price(out_price, student_months=months, class_months=class_months)
        if months and class_months
        else out_price
    )
    prorated_full = (
        prorate_class_price(full_price, student_months=months, class_months=class_months)
        if months and class_months
        else full_price
    )
    enrollment = Enrollment(
        student_id=student.id,
        class_id=school_class.id,
        start_date=enroll_start,
        end_date=end_date,
        register_date=today,
        duration_months=Decimal(str(months)) if months is not None else None,
        total_price=prorated_full,
        discount_price=(prorated_full - prorated_out).quantize(Decimal("0.01")),
        price_after_discount=prorated_out,
        status="Active",
        roster_active=True,
    )
    db.add(enrollment)
    return enrollment


def _deactivate_enrollment(db: Session, *, student_id: int, class_id: int) -> None:
    active = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.class_id == class_id,
            Enrollment.roster_active.is_(True),
        )
    )
    if active is None:
        return
    active.roster_active = False
    if (active.status or "").strip().lower() == "active":
        active.status = "Completed"


def _sync_enrollments_for_invoice_edit(
    db: Session,
    *,
    student: Student,
    old_class_ids: set[int],
    new_class_ids: set[int],
    classes_by_id: dict[int, SchoolClass],
) -> None:
    added = new_class_ids - old_class_ids
    removed = old_class_ids - new_class_ids
    for class_id in removed:
        _deactivate_enrollment(db, student_id=student.id, class_id=class_id)
    for class_id in added:
        school_class = classes_by_id.get(class_id)
        if school_class is None:
            continue
        already_active = db.scalar(
            select(Enrollment.id).where(
                Enrollment.student_id == student.id,
                Enrollment.class_id == class_id,
                Enrollment.roster_active.is_(True),
            )
        )
        if already_active:
            continue
        _create_active_enrollment(db, student=student, school_class=school_class)
    db.flush()


def update_invoice(
    db: Session,
    invoice_id: int,
    payload: InvoiceUpdate,
    *,
    username: str = "system",
) -> InvoiceRead:
    invoice = db.scalar(
        select(Invoice).options(*_invoice_load_options()).where(Invoice.id == invoice_id)
    )
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    old_class_ids = {int(line.class_id) for line in invoice.lines if line.class_id is not None}
    subtotal, discount, total, built_lines = _allocate_discounted_lines(
        payload.lines,
        discount_amount=payload.discount_amount,
    )
    new_class_ids = {class_id for class_id, _, _, _ in built_lines}
    touched_ids = old_class_ids | new_class_ids

    classes_by_id = {
        school_class.id: school_class
        for school_class in db.scalars(
            select(SchoolClass)
            .options(selectinload(SchoolClass.course), selectinload(SchoolClass.teacher))
            .where(SchoolClass.id.in_(touched_ids or {-1}))
        ).all()
    }
    missing = new_class_ids - set(classes_by_id.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown class id(s): {', '.join(str(i) for i in sorted(missing))}",
        )

    # Replace lines (cascade delete-orphan on clear + re-add).
    invoice.lines.clear()
    db.flush()
    for class_id, qty, unit_price, line_total in built_lines:
        invoice.lines.append(
            InvoiceLine(
                class_id=class_id,
                qty=qty,
                price=unit_price,
                total=line_total,
            )
        )
    invoice.subtotal = subtotal
    invoice.discount_amount = discount
    invoice.total = total
    if payload.payment_note is not None:
        invoice.payment_note = (payload.payment_note or "").strip() or None
    method, paid, own, _status = _resolve_payment_amounts(
        total=total,
        payment_method=payload.payment_method if payload.payment_method is not None else invoice.payment_method,
        amount_paid=payload.amount_paid,
        amount_own=payload.amount_own,
    )
    invoice.payment_method = method
    invoice.amount_paid = paid
    invoice.amount_own = own
    if payload.exchange_rate is not None:
        invoice.exchange_rate = _exchange_rate(payload.exchange_rate)

    student = invoice.student
    if student is None and invoice.student_id:
        student = db.get(Student, invoice.student_id)
    if student is not None:
        _sync_enrollments_for_invoice_edit(
            db,
            student=student,
            old_class_ids=old_class_ids,
            new_class_ids=new_class_ids,
            classes_by_id=classes_by_id,
        )

    db.execute(delete(Commission).where(Commission.invoice_id == invoice.id))
    db.flush()
    record_commissions_for_invoice(db, invoice, classes_by_id)

    for class_id in touched_ids:
        school_class = classes_by_id.get(class_id) or db.get(SchoolClass, class_id)
        if school_class is None:
            continue
        ensure_finance_for_class(db, school_class)
        refresh_finance_total_commission(db, class_id)

    write_audit_log(
        db,
        action="Update",
        username=username,
        description=f"Updated invoice {invoice.invoice_no}",
    )
    db.commit()

    from app.core.redis_cache import delete_key
    from app.services.invoice_print_cache import print_cache_key, warm_invoice_print_cache

    delete_key(print_cache_key(invoice.invoice_no))
    warm_invoice_print_cache(db, invoice.id)

    refreshed = get_invoice(db, invoice.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return refreshed


def _clean(value: str | None) -> str:
    return str(value or "").strip()


def _find_or_create_checkout_student(db: Session, payload: InvoiceCheckoutCreate) -> tuple[Student, bool]:
    student = db.get(Student, payload.student_id) if payload.student_id else None
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
        if name_km and not student.name_km:
            student.name_km = name_km
        if name_en and not student.name_en:
            student.name_en = name_en
        db.flush()
        return student, False

    fallback_name = name_en or name_km or customer_name or "Student"
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
    return student, True


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


def create_invoice(
    db: Session,
    payload: InvoiceCreate,
    *,
    username: str = "system",
    commit: bool = True,
) -> InvoiceRead:
    if not payload.lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No invoice lines.")
    for line in payload.lines:
        if not line.class_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each line requires classId.")

    subtotal = sum((line.price * line.qty for line in payload.lines), Decimal("0"))
    discount = Decimal(payload.discount_amount or 0)
    if discount < 0:
        discount = Decimal("0")
    if discount > subtotal:
        discount = subtotal
    total = (subtotal - discount).quantize(Decimal("0.01"))
    method, paid, own, _status = _resolve_payment_amounts(
        total=total,
        payment_method=payload.payment_method,
        amount_paid=payload.amount_paid,
        amount_own=payload.amount_own,
    )
    invoice = Invoice(
        invoice_no=get_next_invoice_no(db),
        student_id=payload.student_id,
        address=payload.address,
        seller=payload.seller,
        payment_note=(payload.payment_note or "").strip() or None,
        payment_method=method,
        amount_paid=paid,
        amount_own=own,
        exchange_rate=_exchange_rate(payload.exchange_rate),
        subtotal=subtotal,
        discount_amount=discount,
        total=total,
    )
    # Line totals are grand total after invoice discount (split proportionally).
    line_bases = [Decimal(line.price) * Decimal(line.qty) for line in payload.lines]
    allocated = Decimal("0")
    for index, line in enumerate(payload.lines):
        base = line_bases[index]
        if index == len(payload.lines) - 1:
            line_total = (total - allocated).quantize(Decimal("0.01"))
        elif subtotal > 0:
            line_total = (base / subtotal * total).quantize(Decimal("0.01"))
            allocated += line_total
        else:
            line_total = Decimal("0")
        qty = Decimal(line.qty or 1)
        unit_price = (line_total / qty).quantize(Decimal("0.01")) if qty else line_total
        invoice.lines.append(
            InvoiceLine(
                class_id=line.class_id,
                qty=line.qty,
                price=unit_price,
                total=line_total,
            )
        )
    db.add(invoice)
    db.flush()
    db.refresh(invoice)
    write_audit_log(db, action="Create", username=username, description=f"Created invoice {invoice.invoice_no}")
    if commit:
        db.commit()
        return get_invoice(db, invoice.id)  # type: ignore[return-value]
    # Ensure relationships available for response before commit
    invoice = db.scalar(
        select(Invoice).options(*_invoice_load_options()).where(Invoice.id == invoice.id)
    )
    return _to_read(invoice)  # type: ignore[arg-type]


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
                qty=qty,
                price=price,
            )
        )

    if not invoice_lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid class lines.")

    new_enrollments = _ensure_checkout_enrollments(db, student=student, classes=classes, payload=payload)

    discount_percent = max(Decimal("0"), min(Decimal(payload.discount_percent or 0), Decimal("100")))
    discount_amount = subtotal * discount_percent / Decimal("100")

    db.info["defer_cache_invalidation"] = True
    try:
        invoice_read = create_invoice(
            db,
            InvoiceCreate(
                student_id=student.id,
                address=(payload.customer_address or "").strip() or (payload.province or "").strip() or None,
                seller=username,
                payment_note=payload.payment_note,
                payment_method=payload.payment_method,
                amount_paid=payload.amount_paid,
                amount_own=payload.amount_own,
                exchange_rate=payload.exchange_rate,
                discount_amount=discount_amount,
                lines=invoice_lines,
            ),
            username=username,
            commit=False,
        )
        persisted = db.scalar(
            select(Invoice).options(*_invoice_load_options()).where(Invoice.id == invoice_read.id)
        )
        if persisted is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invoice was not saved.")
        record_commissions_for_invoice(
            db,
            persisted,
            classes,
        )
        db.commit()
        invoice_read = _to_read(persisted)
    finally:
        db.info.pop("defer_cache_invalidation", None)

    enrollment_ids = [enrollment.id for enrollment, _ in new_enrollments]
    should_notify = bool(student_is_new or new_enrollments)
    job_id = dispatch_checkout_post_process(
        persisted.id,
        student.id,
        is_new_student=student_is_new,
        registered_by=username,
        notify=should_notify,
        enrollment_ids=enrollment_ids,
        invoice_no=persisted.invoice_no,
    )

    return InvoiceCheckoutResponse(
        invoice_no=invoice_read.invoice_no,
        subtotal=invoice_read.subtotal,
        discount_amount=invoice_read.discount_amount,
        total=invoice_read.total,
        invoice=invoice_read,
        job_id=job_id,
        print_status="ready" if job_id is None else "pending",
    )


def pay_invoice_own(
    db: Session,
    invoice_id: int,
    payload: InvoicePayOwn,
    *,
    username: str = "system",
) -> InvoiceRead:
    invoice = db.scalar(
        select(Invoice).options(*_invoice_load_options()).where(Invoice.id == invoice_id)
    )
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    remaining = _money(invoice.amount_own)
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invoice has no remaining own balance.",
        )

    pay_amount = _money(payload.amount)
    if pay_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than zero.",
        )
    if pay_amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount cannot exceed remaining own (${remaining}).",
        )

    invoice.amount_paid = (_money(invoice.amount_paid) + pay_amount).quantize(Decimal("0.01"))
    invoice.amount_own = (remaining - pay_amount).quantize(Decimal("0.01"))
    if invoice.amount_own <= 0:
        invoice.amount_own = Decimal("0.00")
        invoice.amount_paid = _money(invoice.total)
        invoice.payment_method = "cash"

    write_audit_log(
        db,
        action="Update",
        username=username,
        description=f"Paid ${pay_amount} toward own balance on invoice {invoice.invoice_no}",
    )
    db.commit()

    from app.core.redis_cache import delete_key
    from app.services.invoice_print_cache import print_cache_key, warm_invoice_print_cache

    delete_key(print_cache_key(invoice.invoice_no))
    warm_invoice_print_cache(db, invoice.id)

    refreshed = get_invoice(db, invoice.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return refreshed
