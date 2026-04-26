from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.settings import PersistenceSettings, build_persistence_settings


PERSISTENCE_BOUNDARY_VERSION = "persistence-boundary-v1"


class PersistenceConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DatabaseEngineFactory:
    settings: PersistenceSettings
    boundary_version: str = PERSISTENCE_BOUNDARY_VERSION

    @property
    def safe_diagnostics(self) -> dict[str, object]:
        return {
            "boundary_version": self.boundary_version,
            "lazy": True,
            "opens_connection_on_import": False,
            **self.settings.safe_diagnostics,
        }

    def create_engine(self) -> Any:
        if not self.settings._database_url:
            raise PersistenceConfigurationError("DATABASE_URL is required before creating a database engine.")

        create_engine = _load_sqlalchemy_create_engine()
        connect_args = {"connect_timeout": self.settings.connect_timeout_seconds}
        return create_engine(
            self.settings._database_url,
            future=True,
            pool_pre_ping=self.settings.pool_pre_ping,
            echo=self.settings.echo_sql,
            connect_args=connect_args,
        )

    def create_session_factory(self) -> Any:
        engine = self.create_engine()
        sessionmaker = _load_sqlalchemy_sessionmaker()
        return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def create_session(self) -> Any:
        return self.create_session_factory()()


def build_engine_factory(settings: PersistenceSettings | None = None) -> DatabaseEngineFactory:
    return DatabaseEngineFactory(settings=settings or build_persistence_settings())


def _load_sqlalchemy_create_engine() -> Callable[..., Any]:
    try:
        from sqlalchemy import create_engine
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on local optional install state.
        raise PersistenceConfigurationError("SQLAlchemy is required to create a database engine.") from exc
    return create_engine


def _load_sqlalchemy_sessionmaker() -> Callable[..., Any]:
    try:
        from sqlalchemy.orm import sessionmaker
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on local optional install state.
        raise PersistenceConfigurationError("SQLAlchemy is required to create a session factory.") from exc
    return sessionmaker
