from datetime import datetime
from decimal import Decimal

from app.schemas.common import CamelModel


class ReportSalesLineRead(CamelModel):
    no: int
    invoice_no: str
    student_id: int | None = None
    student_name: str | None = None
    student_phone: str | None = None
    phone_customer: str | None = None
    address: str | None = None
    seller: str | None = None
    source: str | None = None
    amount: Decimal
    date: datetime
    product: str | None = None
    class_name: str | None = None
    customer: str | None = None
    receipt: str | None = None
