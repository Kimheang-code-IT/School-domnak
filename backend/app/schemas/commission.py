from datetime import datetime
from decimal import Decimal

from app.schemas.common import CamelModel


class CommissionRead(CamelModel):
    id: int
    class_id: int | None = None
    student_id: int | None = None
    invoice_id: int | None = None
    teacher_id: int | None = None
    class_name: str | None = None
    student_name: str | None = None
    teacher_name: str
    date: datetime
    amount: Decimal
    commission: Decimal
    sale_count: int | None = None
