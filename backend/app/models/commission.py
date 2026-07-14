from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.class_model import SchoolClass
    from app.models.invoice import Invoice
    from app.models.student import Student
    from app.models.user import User


class Commission(Base):
    __tablename__ = "commissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True, index=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    school_class: Mapped["SchoolClass | None"] = relationship(back_populates="commissions")
    student: Mapped["Student | None"] = relationship()
    invoice: Mapped["Invoice | None"] = relationship()
    teacher: Mapped["User | None"] = relationship()
