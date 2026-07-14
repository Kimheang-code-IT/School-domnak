from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.class_model import SchoolClass
    from app.models.student import Student


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seller: Mapped[str | None] = mapped_column(String(150), nullable=True)
    payment_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    amount_own: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=4100)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    student: Mapped["Student | None"] = relationship(back_populates="invoices")
    lines: Mapped[list["InvoiceLine"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    qty: Mapped[int] = mapped_column(default=1)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")
    school_class: Mapped["SchoolClass | None"] = relationship()
