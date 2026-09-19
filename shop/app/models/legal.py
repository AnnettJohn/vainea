from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LegalPage(Base):
    """Redaktionell pflegbare Rechtsseite (Impressum, Datenschutz, AGB, Widerruf).

    Die Texte stehen bewusst in der Datenbank statt im Code: sie werden nach
    juristischer Prüfung eingetragen und später geändert, ohne dass dafür ein
    Deploy nötig ist (siehe Pflichtenheft, offener Punkt "Rechtstexte").

    `body` ist kein HTML, sondern ein bewusst enges Markdown-Subset, das
    `app.core.legal.render_legal_body()` serverseitig in HTML übersetzt und
    dabei alles escaped. So kann aus dem Admin heraus kein Skript auf die
    öffentliche Seite gelangen, auch nicht bei einem kompromittierten
    Admin-Zugang.
    """

    __tablename__ = "legal_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Solange unveröffentlicht, zeigt die Seite den Platzhalterhinweis statt
    # eines halbfertigen Textes - eine leere Rechtsseite wäre schlimmer als
    # ein ehrlicher Hinweis, dass der Text noch geprüft wird.
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    meta_title: Mapped[str | None] = mapped_column(String(70), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(160), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __str__(self) -> str:
        return self.title
