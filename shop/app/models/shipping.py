import uuid

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShippingZone(Base):
    """Versandzone (z. B. Deutschland, EU, Rest der Welt).

    Konkrete Zonen/Länder/Tarife sind laut Pflichtenheft noch offen und
    werden hier bewusst nicht vorbelegt (siehe Rückfrage zu Versandzonen).
    """

    __tablename__ = "shipping_zones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country_codes: Mapped[list[str]] = mapped_column(ARRAY(String(2)), nullable=False, default=list)
    free_shipping_threshold: Mapped[Numeric | None] = mapped_column(Numeric(10, 2), nullable=True)

    rates: Mapped[list["ShippingRate"]] = relationship(
        back_populates="zone", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.name


class ShippingRate(Base):
    """Preis je Versandmethode innerhalb einer Zone (z. B. Standard, Express)."""

    __tablename__ = "shipping_rates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipping_zones.id", ondelete="CASCADE"), nullable=False
    )
    method_name: Mapped[str] = mapped_column(String(60), nullable=False)
    price: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)

    zone: Mapped["ShippingZone"] = relationship(back_populates="rates")

    def __str__(self) -> str:
        return f"{self.method_name} ({self.zone_id})"
