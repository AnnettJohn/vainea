import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.base import Base
from app.models import *  # noqa: F401,F403  (registriert alle Modelle auf Base.metadata)

# Erst NACH app.models importieren: fastapi_users.db (von app.models.user
# eingebunden) und fastapi_users_db_sqlalchemy haben einen zirkulären Import
# (fastapi_users_db_sqlalchemy/__init__.py importiert seinerseits aus
# fastapi_users.db.base). Wird .generics zuerst importiert, verliert
# fastapi_users.db seine SQLAlchemy-Re-Exports dauerhaft für den Prozess.
# Absichtlich nicht mit den obigen Imports zusammengefasst: ein
# isort/ruff-Autofix würde diese Reihenfolge alphabetisch "korrigieren" und
# genau diesen Zirkelbezug wieder einführen.
from fastapi_users_db_sqlalchemy.generics import GUID

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """FastAPI-Users' GUID-Typ (User/OAuthAccount-IDs) als sa.UUID() rendern,
    statt eines Imports der internen fastapi_users_db_sqlalchemy-Klasse in
    der generierten Migration."""
    if type_ == "type" and isinstance(obj, GUID):
        return "sa.UUID()"
    return False


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_item=render_item)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
