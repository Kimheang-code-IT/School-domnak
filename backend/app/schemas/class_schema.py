from datetime import datetime
from decimal import Decimal

from app.schemas.common import CamelModel


class ClassBase(CamelModel):
    name: str
    image: str | None = None
    category_id: int | None = None
    course_id: int | None = None
    teacher_id: int | None = None
    teacher_name: str | None = None
    level: str | None = None
    level_km: str | None = None
    class_duration: str | None = None
    days_of_week: list[str] = []
    time_in: str | None = None
    time_out: str | None = None
    time_slot: str | None = None
    full_price: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    out_price: Decimal = Decimal("0")
    status: str = "Active"


class ClassCreate(ClassBase):
    pass


class ClassUpdate(CamelModel):
    name: str | None = None
    image: str | None = None
    category_id: int | None = None
    course_id: int | None = None
    teacher_id: int | None = None
    teacher_name: str | None = None
    level: str | None = None
    level_km: str | None = None
    class_duration: str | None = None
    days_of_week: list[str] | None = None
    time_in: str | None = None
    time_out: str | None = None
    time_slot: str | None = None
    full_price: Decimal | None = None
    discount_amount: Decimal | None = None
    out_price: Decimal | None = None
    status: str | None = None


class ClassRead(ClassBase):
    id: int
    category: str | None = None
    course_name: str | None = None
    student_count: int = 0
    created_at: datetime | None = None
