from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.class_model import SchoolClass
    from app.models.student import Student


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    price_after_discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    register_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_months: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active")
    roster_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    student: Mapped["Student"] = relationship(back_populates="enrollments")
    school_class: Mapped["SchoolClass"] = relationship(back_populates="enrollments")
