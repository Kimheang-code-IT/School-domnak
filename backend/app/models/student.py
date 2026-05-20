from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.invoice import Invoice


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    name_km: Mapped[str] = mapped_column(String(180), index=True)
    name_en: Mapped[str] = mapped_column(String(180), index=True)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    province: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="student")
