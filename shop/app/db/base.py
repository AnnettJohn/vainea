from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Gemeinsame Basisklasse für alle SQLAlchemy-Modelle.

    Wird in app/db/base_models.py um alle Modelle ergänzt importiert,
    damit Alembic sie beim Autogenerate sieht.
    """
