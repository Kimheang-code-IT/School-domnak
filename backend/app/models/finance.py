from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.class_model import SchoolClass


class Finance(Base):
    __tablename__ = "finance"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), unique=True, nullable=True)
    electricity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    water: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    internet: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    facebook: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    other: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    final_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    in_price_for_pos: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    school_class: Mapped["SchoolClass | None"] = relationship(back_populates="finance")
