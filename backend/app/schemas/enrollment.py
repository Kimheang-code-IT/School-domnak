from datetime import date
from decimal import Decimal

from app.schemas.common import CamelModel


class EnrollmentCreate(CamelModel):
    student_id: int
    class_id: int
    start_date: date | None = None
    end_date: date | None = None
    total_price: Decimal = Decimal("0")
    discount_price: Decimal = Decimal("0")
    price_after_discount: Decimal = Decimal("0")
    register_date: date | None = None
    status: str = "Active"


class EnrollmentPatch(CamelModel):
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    roster_active: bool | None = None


class ClassEnrollmentRead(CamelModel):
    id: int
    student_id: int
    student_code: str
    student_name: str
    name_km: str | None = None
    name_en: str | None = None
    gender: str | None = None
    phone: str | None = None
    birthdate: date | None = None
    province: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    startdate: date | None = None
    enddate: date | None = None
    status: str
    expires_soon: bool = False
    duration_months: Decimal | None = None
    total_price: Decimal = Decimal("0")
    discount_price: Decimal = Decimal("0")
    price_after_discount: Decimal = Decimal("0")


class StudentEnrollmentRead(CamelModel):
    id: int
    status: str | None = None
    roster_active: bool | None = None
    course_name: str | None = None
    course_name_km: str | None = None
    class_name: str | None = None
    level: str | None = None
    level_km: str | None = None
    level_name_km: str | None = None
    class_duration: str | None = None
    duration_months: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    total_price: Decimal = Decimal("0")
    discount_price: Decimal = Decimal("0")
    price_after_discount: Decimal = Decimal("0")
    invoice_discount_amount: Decimal | None = None
    invoice_grand_total: Decimal | None = None
    register_date: date | None = None
    name_km: str | None = None
    name_en: str | None = None
    birthdate: date | None = None
    gender: str | None = None
