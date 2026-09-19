from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class State(Base):
    """Einer der vier Marken-States (Sea, Dream, Light, Sun).

    Felder 1:1 aus dem STATES-Array des Click-Dummys übernommen (hex, mood,
    line als brand_line, img/circle als *_image_url, pos als
    hero_image_position, story als story_text).
    """

    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    num: Mapped[str] = mapped_column(String(2), nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    hex_color: Mapped[str] = mapped_column(String(7), nullable=False)
    mood_text: Mapped[str] = mapped_column(String(200), nullable=False)
    brand_line: Mapped[str] = mapped_column(String(100), nullable=False)
    story_text: Mapped[str] = mapped_column(Text, nullable=False)

    hero_image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    hero_image_position: Mapped[str] = mapped_column(String(20), default="50% 50%")
    circle_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Redigierbare Meta-Title/-Description je Seite (SEO, siehe Pflichtenheft,
    # nicht-funktionale Anforderungen); leer = Fallback auf generierten Titel.
    meta_title: Mapped[str | None] = mapped_column(String(70), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(160), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    products: Mapped[list["Product"]] = relationship(back_populates="state")

    def __str__(self) -> str:
        return self.name
