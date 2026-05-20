from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.class_model import SchoolClass
from app.models.enrollment import Enrollment
from app.models.invoice import Invoice
from app.models.student import Student


def _split_student_display_name(raw: str | None) -> tuple[str, str]:
    text = str(raw or "").strip()
    if not text:
        return "", ""
    if " · " in text:
        parts = [part.strip() for part in text.split(" · ") if part.strip()]
        if len(parts) >= 2:
            return parts[0], " · ".join(parts[1:])
        return parts[0], ""
    return text, ""


def _iso_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _build_preview_from_invoice(db: Session, invoice: Invoice) -> dict:
    student: Student | None = invoice.student
    if student is None and invoice.student_id:
        student = db.get(Student, invoice.student_id)

    name_km = student.name_km if student else ""
    name_en = student.name_en if student else ""
    if not name_km and not name_en:
        name_km, name_en = _split_student_display_name(invoice.student_name)

    customer = invoice.student_name or (
        " · ".join([part for part in [name_km, name_en] if part]) or name_en or name_km
    )

    lines_payload: list[dict] = []
    for line in invoice.lines:
        school_class: SchoolClass | None = None
        course_name: str | None = None
        enrollment: Enrollment | None = None

        if line.class_id:
            school_class = db.scalar(
                select(SchoolClass)
                .options(selectinload(SchoolClass.course))
                .where(SchoolClass.id == line.class_id)
            )
            if school_class and school_class.course:
                course_name = school_class.course.course_name

            if student and line.class_id:
                enrollment = db.scalar(
                    select(Enrollment)
                    .where(
                        Enrollment.student_id == student.id,
                        Enrollment.class_id == line.class_id,
                    )
                    .order_by(Enrollment.id.desc())
                )

        class_name = school_class.name if school_class else line.product_name
        start_date = enrollment.start_date if enrollment else invoice.created_at.date()
        end_date = enrollment.end_date if enrollment else None

        lines_payload.append(
            {
                "invoiceNo": invoice.invoice_no,
                "date": invoice.created_at.isoformat(),
                "startDate": _iso_date(start_date),
                "endDate": _iso_date(end_date),
                "registeredAt": _iso_date(enrollment.register_date if enrollment else start_date),
                "product": class_name,
                "courseName": course_name or class_name,
                "timeSlot": school_class.time_slot if school_class else None,
                "timeIn": school_class.time_in if school_class else None,
                "timeOut": school_class.time_out if school_class else None,
                "classDuration": school_class.class_duration if school_class else None,
                "daysOfWeek": list(school_class.days_of_week or []) if school_class else [],
                "classImage": school_class.image if school_class else None,
                "studentName": customer,
                "nameKm": name_km,
                "nameEn": name_en,
                "customer": customer,
                "phoneCustomer": invoice.student_phone or (student.phone if student else None),
                "seller": invoice.seller,
                "source": invoice.source,
                "address": invoice.address,
                "amount": float(line.total or 0),
                "grandTotal": float(invoice.total or 0),
                "qty": int(line.qty or 1),
                "description": class_name,
            }
        )

    if not lines_payload:
        lines_payload.append(
            {
                "invoiceNo": invoice.invoice_no,
                "date": invoice.created_at.isoformat(),
                "product": "—",
                "courseName": "—",
                "studentName": customer,
                "nameKm": name_km,
                "nameEn": name_en,
                "customer": customer,
                "phoneCustomer": invoice.student_phone,
                "seller": invoice.seller,
                "source": invoice.source,
                "address": invoice.address,
                "amount": float(invoice.total or 0),
                "grandTotal": float(invoice.total or 0),
                "qty": 1,
            }
        )

    head = lines_payload[0]
    return {
        **head,
        "lines": lines_payload,
    }


def get_invoice_preview_by_no(db: Session, invoice_no: str) -> dict | None:
    invoice = db.scalar(
        select(Invoice)
        .options(
            selectinload(Invoice.lines),
            selectinload(Invoice.student),
        )
        .where(Invoice.invoice_no == invoice_no.strip())
    )
    if not invoice:
        return None
    return _build_preview_from_invoice(db, invoice)


def enrich_preview_payloads(db: Session, payloads: list[dict]) -> list[dict]:
    enriched: list[dict] = []
    for raw in payloads:
        invoice_no = str(raw.get("invoiceNo") or raw.get("invoice_no") or "").strip()
        if invoice_no:
            preview = get_invoice_preview_by_no(db, invoice_no)
            if preview:
                enriched.append(preview)
                continue
        amount = raw.get("amount")
        if amount is None:
            amount = raw.get("grandTotal", 0)
        enriched.append(
            {
                "invoiceNo": invoice_no or str(raw.get("invoiceNo") or ""),
                "date": raw.get("date"),
                "endDate": raw.get("endDate"),
                "registeredAt": raw.get("registeredAt"),
                "product": raw.get("product"),
                "courseName": raw.get("courseName") or raw.get("product"),
                "studentName": raw.get("studentName") or raw.get("customer"),
                "nameKm": raw.get("nameKm"),
                "nameEn": raw.get("nameEn"),
                "customer": raw.get("customer") or raw.get("studentName"),
                "phoneCustomer": raw.get("phoneCustomer"),
                "seller": raw.get("seller"),
                "source": raw.get("source"),
                "address": raw.get("address"),
                "amount": float(amount or 0),
                "grandTotal": float(raw.get("grandTotal") or amount or 0),
                "qty": int(raw.get("qty") or 1),
                "description": raw.get("product"),
            }
        )
    return enriched
