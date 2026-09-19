import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class DiscountCode(Base):
    """Rabattcode, prozentual oder als Festbetrag.

    Wird auf die Zwischensumme angewendet, bevor der Versand addiert wird;
    die Freigrenze für kostenlosen Versand bezieht sich auf den Warenwert
    vor Rabatt (siehe Pflichtenheft).
    """

    __tablename__ = "discount_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    type: Mapped[DiscountType] = mapped_column(SAEnum(DiscountType, name="discount_type"), nullable=False)
    value: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)

    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    usage_limit_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_limit_per_customer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    min_order_value: Mapped[Numeric | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __str__(self) -> str:
        return self.code
