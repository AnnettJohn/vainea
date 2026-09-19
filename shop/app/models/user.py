import uuid

from fastapi_users.db import SQLAlchemyBaseOAuthAccountTableUUID, SQLAlchemyBaseUserTableUUID
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    """Social-Login-Verknüpfung (optional, siehe Pflichtenheft User-Entität).

    Wird von FastAPI-Users bereitgestellt und ist von Anfang an mitgeführt,
    auch wenn zum Start nur klassischer E-Mail/Passwort-Login aktiv ist.
    """

    __tablename__ = "oauth_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Kundenkonto via FastAPI-Users (id, email, password_hash kommen aus der Basisklasse)."""

    __tablename__ = "users"

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount", lazy="joined", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.email
