from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.class_model import SchoolClass


class Commission(Base):
    __tablename__ = "commissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    student_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    teacher_name: Mapped[str] = mapped_column(String(150), index=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    school_class: Mapped["SchoolClass | None"] = relationship(back_populates="commissions")
