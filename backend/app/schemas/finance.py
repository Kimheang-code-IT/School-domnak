from decimal import Decimal

from app.schemas.common import CamelModel


class FinanceUpdate(CamelModel):
    electricity: Decimal | None = None
    water: Decimal | None = None
    internet: Decimal | None = None
    total_commission: Decimal | None = None
    facebook: Decimal | None = None
    other: Decimal | None = None


class FinanceRead(CamelModel):
    id: int
    class_name: str | None = None
    product_name: str | None = None
    electricity: Decimal
    water: Decimal
    internet: Decimal
    total_commission: Decimal
    facebook: Decimal
    other: Decimal
    amount: Decimal
    print_price: Decimal | None = None
    final_price: Decimal
    in_price_for_pos: Decimal
