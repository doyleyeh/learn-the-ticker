from __future__ import annotations

from logging.config import fileConfig

from backend.db import build_engine_factory
from backend.persistence import target_metadata
from backend.settings import build_persistence_settings, offline_migration_database_url

try:
    from alembic import context
except ModuleNotFoundError:  # pragma: no cover - local tests inspect this file without Alembic installed.
    context = None


if context is not None:
    config = context.config
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)
else:
    config = None


def run_migrations_offline() -> None:
    if context is None:
        raise RuntimeError("Alembic is required to run migrations.")

    settings = build_persistence_settings()
    context.configure(
        url=offline_migration_database_url(settings),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    if context is None:
        raise RuntimeError("Alembic is required to run migrations.")

    settings = build_persistence_settings()
    engine = build_engine_factory(settings).create_engine()

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context is not None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
