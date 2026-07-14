from decimal import Decimal

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models.class_model import SchoolClass
from app.models.invoice import Invoice, InvoiceLine
from app.models.student import Student
from app.schemas.common import TableQueryParams
from app.schemas.report import ReportSalesLineRead
from app.utils.filters import apply_date_filter, apply_search, split_filter, split_int_filter
from app.utils.pagination import apply_pagination, get_offset
from app.utils.sorting import apply_sorting


def _english_student_name(student: Student | None) -> str | None:
    if student is None:
        return None
    en = (student.name_en or "").strip()
    if en:
        return en
    km = (student.name_km or "").strip()
    return km or None


class ReportRepository:
    def list_sales_lines(
        self,
        db: Session,
        query: TableQueryParams,
        *,
        product: str | None = None,
        address: str | None = None,
        seller: str | None = None,
        class_id: str | None = None,
        course_id: str | None = None,
        export: bool = False,
    ) -> tuple[list[ReportSalesLineRead], int]:
        statement = (
            select(InvoiceLine, Invoice, Student, SchoolClass)
            .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
            .outerjoin(Student, Student.id == Invoice.student_id)
            .outerjoin(SchoolClass, SchoolClass.id == InvoiceLine.class_id)
        )
        products = split_filter(product)
        if products:
            statement = statement.where(SchoolClass.name.in_(products))

        addresses = split_filter(address)
        if addresses:
            statement = statement.where(
                or_(
                    Invoice.address.in_(addresses),
                    Student.province.in_(addresses),
                )
            )

        sellers = split_filter(seller)
        if sellers:
            statement = statement.where(Invoice.seller.in_(sellers))

        class_ids = split_int_filter(class_id)
        if class_ids:
            statement = statement.where(InvoiceLine.class_id.in_(class_ids))

        course_ids = split_int_filter(course_id)
        if course_ids:
            statement = statement.where(SchoolClass.course_id.in_(course_ids))
        statement = apply_search(
            statement,
            query.search,
            [
                Invoice.invoice_no,
                Student.name_en,
                Student.name_km,
                Student.phone,
                Invoice.address,
                Invoice.seller,
                SchoolClass.name,
                Student.province,
                cast(Student.id, String),
                cast(Invoice.student_id, String),
            ],
        )
        statement = apply_date_filter(statement, Invoice.created_at, query.date_from, query.date_to)
        total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
        statement = apply_sorting(
            statement,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            sort_map={
                "invoiceNo": Invoice.invoice_no,
                "studentId": Invoice.student_id,
                "studentName": Student.name_en,
                "studentPhone": Student.phone,
                "product": SchoolClass.name,
                "className": SchoolClass.name,
                "address": Invoice.address,
                "seller": Invoice.seller,
                "amount": InvoiceLine.total,
                "date": Invoice.created_at,
            },
            default_sort="date",
        )
        if not export:
            statement = apply_pagination(statement, query.page, query.limit)
        rows = db.execute(statement).all()
        start_no = 1 if export else get_offset(query.page, query.limit) + 1
        data = []
        for index, (line, invoice, student, school_class) in enumerate(rows, start=start_no):
            resolved_address = (invoice.address or "").strip()
            if not resolved_address and student is not None:
                resolved_address = (student.province or "").strip()
            display_name = _english_student_name(student)
            sid = student.id if student is not None else invoice.student_id
            phone = student.phone if student is not None else None
            class_name = school_class.name if school_class else None
            amount_own = Decimal(invoice.amount_own or 0)
            amount_paid = Decimal(invoice.amount_paid or 0)
            payment_status = "own" if amount_own > 0 else "paid"
            payment_method = (invoice.payment_method or ("own" if amount_own > 0 else "cash"))
            data.append(
                ReportSalesLineRead(
                    no=index,
                    invoice_id=invoice.id,
                    invoice_no=invoice.invoice_no,
                    student_id=sid,
                    student_name=display_name,
                    student_phone=phone,
                    phone_customer=phone,
                    address=resolved_address or None,
                    seller=invoice.seller,
                    amount=line.total,
                    amount_paid=amount_paid,
                    amount_own=amount_own,
                    exchange_rate=Decimal(invoice.exchange_rate or 4100),
                    payment_method=payment_method,
                    payment_status=payment_status,
                    date=invoice.created_at,
                    product=class_name,
                    class_name=class_name,
                    customer=display_name,
                    receipt=invoice.invoice_no,
                )
            )
        return data, total
