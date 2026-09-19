import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Product(Base):
    """Zentrale Produkttabelle, ersetzt das flache PRODUCTS-Array des Dummys.

    `product_group_id` verbindet Farbvarianten desselben Designs über die
    States hinweg (z. B. alle "Mono Robe"-Varianten oder alle "Spa Bag"
    -Farbstellungen) und bildet damit die im Dummy per `productInState()`
    gelöste Swatch-Navigation serverseitig ab. Es ist bewusst kein Fremd-
    schlüssel auf eine eigene Tabelle, sondern ein gemeinsamer Gruppen-
    schlüssel (String), da das Pflichtenheft keine eigene ProductGroup-
    Entität vorsieht.
    """

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id", ondelete="RESTRICT"), nullable=False)
    material: Mapped[str] = mapped_column(String(60), nullable=False)
    price: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_new: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_bestseller: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    variant: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        SAEnum(ProductStatus, name="product_status"), default=ProductStatus.ACTIVE, nullable=False
    )
    product_group_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)

    # Redigierbare Meta-Title/-Description je Seite (SEO, siehe Pflichtenheft,
    # nicht-funktionale Anforderungen); leer = Fallback auf generierten Titel.
    meta_title: Mapped[str | None] = mapped_column(String(70), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(160), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    state: Mapped["State"] = relationship(back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order"
    )
    sizes: Mapped[list["ProductSize"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.name


class ProductImage(Base):
    """Mehrere Bilder pro Produkt statt einzelnem img-Feld wie im Dummy."""

    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(200), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="images")

    def __str__(self) -> str:
        return self.url


class ProductSize(Base):
    """Lagerbestand je Größe statt reiner Anzeigeoption wie im Dummy."""

    __tablename__ = "product_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="sizes")

    def __str__(self) -> str:
        return f"{self.sku} ({self.size})"
