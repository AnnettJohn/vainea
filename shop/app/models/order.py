import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELED = "canceled"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    REFUNDED = "refunded"


class Order(Base):
    """Bestellung inkl. der zum Bestellzeitpunkt fixierten Preise.

    shipping_cost, discount_code und discount_amount werden bei Anlage der
    Bestellung als Schnappschuss gespeichert, damit spätere Änderungen an
    Versandtarifen oder Rabattcodes bestehende Bestellungen nicht
    verändern (siehe Pflichtenheft).
    """

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"), default=OrderStatus.PENDING, nullable=False
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Lieferadresse
    shipping_name: Mapped[str] = mapped_column(String(200), nullable=False)
    shipping_street: Mapped[str] = mapped_column(String(200), nullable=False)
    shipping_zip: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_city: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_country: Mapped[str] = mapped_column(String(2), nullable=False)

    # Rechnungsadresse
    billing_name: Mapped[str] = mapped_column(String(200), nullable=False)
    billing_street: Mapped[str] = mapped_column(String(200), nullable=False)
    billing_zip: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_city: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_country: Mapped[str] = mapped_column(String(2), nullable=False)

    shipping_method_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    shipping_cost: Mapped[Numeric] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    discount_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    discount_amount: Mapped[Numeric] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    subtotal: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    total: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)

    mollie_payment_id: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")

    def __str__(self) -> str:
        return self.order_number


class OrderItem(Base):
    """Bestellposition mit Preis-Schnappschuss zum Bestellzeitpunkt."""

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )

    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    sku: Mapped[str] = mapped_column(String(60), nullable=False)
    unit_price: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    line_total: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product | None"] = relationship()
