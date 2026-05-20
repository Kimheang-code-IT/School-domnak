from datetime import datetime
from decimal import Decimal

from app.schemas.common import CamelModel


class CommissionRead(CamelModel):
    id: int
    class_name: str | None = None
    student_name: str | None = None
    teacher_name: str
    source: str | None = None
    date: datetime
    amount: Decimal
    commission: Decimal
    sale_count: int | None = None
