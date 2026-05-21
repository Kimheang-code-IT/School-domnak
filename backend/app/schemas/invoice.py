from datetime import date, datetime
from decimal import Decimal

from app.schemas.common import CamelModel


class InvoiceLineCreate(CamelModel):
    class_id: int | None = None
    product_name: str
    qty: int = 1
    price: Decimal = Decimal("0")


class InvoiceCreate(CamelModel):
    student_id: int | None = None
    student_name: str | None = None
    student_phone: str | None = None
    address: str | None = None
    seller: str | None = None
    source: str | None = None
    discount_amount: Decimal = Decimal("0")
    lines: list[InvoiceLineCreate]


class InvoiceCheckoutLine(CamelModel):
    product_id: int
    qty: int = 1


class InvoiceCheckoutCreate(CamelModel):
    student_id: int | None = None
    image: str | None = None
    name_km: str | None = None
    name_en: str | None = None
    gender: str | None = None
    birthdate: date | None = None
    province: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_address: str | None = None
    source: str | None = None
    delivery_type: str | None = None
    delivery_price: Decimal = Decimal("0")
    delivery_date: str | None = None
    discount_percent: Decimal = Decimal("0")
    payment_method: str | None = None
    delivery_status: str | None = None
    seller_id: int | None = None
    duration_months: float | None = None
    start_date: date | None = None
    lines: list[InvoiceCheckoutLine]


class InvoiceProduct(CamelModel):
    name: str
    out_price: Decimal


class InvoiceLineRead(CamelModel):
    id: int
    product: InvoiceProduct
    product_name: str
    qty: int
    price: Decimal
    total: Decimal


class InvoiceRead(CamelModel):
    id: int
    invoice_no: str
    student_id: int | None = None
    student_name: str | None = None
    student_phone: str | None = None
    address: str | None = None
    seller: str | None = None
    source: str | None = None
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal
    created_at: datetime
    lines: list[InvoiceLineRead]


class InvoiceNumberRead(CamelModel):
    invoice_no: str


class InvoiceCheckoutResponse(CamelModel):
    invoice_no: str
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal
    invoice: InvoiceRead
    job_id: str | None = None
    print_status: str = "pending"


class CheckoutJobStatusRead(CamelModel):
    status: str
    print_ready: bool = False
    invoice_no: str | None = None
    error: str | None = None


class InvoicePreviewInput(CamelModel):
    invoice_no: str | None = None
    date: str | None = None
    product: str | None = None
    customer: str | None = None
    phone_customer: str | None = None
    seller: str | None = None
    source: str | None = None
    address: str | None = None
    amount: Decimal | float | None = None


class InvoicePreviewSessionCreate(CamelModel):
    invoices: list[InvoicePreviewInput]


class InvoicePreviewSessionRead(CamelModel):
    preview_key: str


class InvoicePreviewBundleRead(CamelModel):
    invoices: list[dict]
    invoice: dict | None = None
