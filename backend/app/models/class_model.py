from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.commission import Commission
    from app.models.course import Course
    from app.models.enrollment import Enrollment
    from app.models.finance import Finance
    from app.models.level import Level
    from app.models.user import User


class SchoolClass(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    level_id: Mapped[int | None] = mapped_column(ForeignKey("levels.id"), nullable=True, index=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    teacher_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    level_km: Mapped[str | None] = mapped_column(String(100), nullable=True)
    class_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    days_of_week: Mapped[list[str]] = mapped_column(JSON, default=list)
    time_in: Mapped[str | None] = mapped_column(String(50), nullable=True)
    time_out: Mapped[str | None] = mapped_column(String(50), nullable=True)
    time_slot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    full_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    out_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    teacher_commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    teacher_commission_mode: Mapped[str] = mapped_column(String(20), default="usd")
    teacher_commission_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    status: Mapped[str] = mapped_column(String(50), default="Active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    category: Mapped["Category | None"] = relationship(back_populates="classes")
    course: Mapped["Course | None"] = relationship(back_populates="classes")
    level_ref: Mapped["Level | None"] = relationship(back_populates="classes")
    teacher: Mapped["User | None"] = relationship(back_populates="classes")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="school_class")
    finance: Mapped["Finance | None"] = relationship(back_populates="school_class")
    commissions: Mapped[list["Commission"]] = relationship(back_populates="school_class")
