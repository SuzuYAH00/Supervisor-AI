from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from zoneinfo import ZoneInfo

from sqlalchemy import URL, Engine, create_engine, event, text
from sqlalchemy.exc import DBAPIError, OperationalError

from supervisor_ai.core.config import MkDatabaseSettings

MK_SOURCE_TIMEZONE = ZoneInfo("America/Fortaleza")
_POOL_SIZE = 2
_POOL_MAX_OVERFLOW = 0
_POOL_RECYCLE_SECONDS = 300
_POOL_TIMEOUT_SECONDS = 5


class MkDatabaseConfigurationError(RuntimeError):
    """A configuração externa do MK está ausente ou incompleta."""


class MkDatabaseStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class MkDatabaseErrorKind(StrEnum):
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    DATABASE_UNAVAILABLE = "database_unavailable"
    QUERY = "query"


@dataclass(frozen=True, slots=True)
class MkDatabaseHealth:
    status: MkDatabaseStatus
    read_only: bool
    error_kind: MkDatabaseErrorKind | None = None


class MkDatabaseConnector:
    """Acesso estritamente de leitura ao PostgreSQL externo do MK."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def check_health(self) -> MkDatabaseHealth:
        try:
            with self._engine.connect() as connection:
                alive = connection.scalar(text("SELECT 1")) == 1
                read_only = connection.scalar(
                    text("SHOW transaction_read_only")
                ) == "on"
            if alive and read_only:
                return MkDatabaseHealth(MkDatabaseStatus.AVAILABLE, True)
            return MkDatabaseHealth(
                MkDatabaseStatus.UNAVAILABLE,
                read_only,
                MkDatabaseErrorKind.QUERY,
            )
        except (OperationalError, DBAPIError) as error:
            return MkDatabaseHealth(
                MkDatabaseStatus.UNAVAILABLE,
                False,
                _safe_error_kind(error),
            )

    def dispose(self) -> None:
        self._engine.dispose()


def create_mk_database_connector(
    settings: MkDatabaseSettings,
) -> MkDatabaseConnector | None:
    configured = (
        settings.mk_db_host,
        settings.mk_db_name,
        settings.mk_db_user,
        settings.mk_db_password,
    )
    if not any(value is not None for value in configured):
        return None
    if any(value is None for value in configured):
        raise MkDatabaseConfigurationError(
            "MK database configuration is incomplete"
        )
    if settings.mk_db_connect_timeout_seconds <= 0:
        raise MkDatabaseConfigurationError(
            "MK database connect timeout must be positive"
        )
    if settings.mk_db_statement_timeout_ms <= 0:
        raise MkDatabaseConfigurationError(
            "MK database statement timeout must be positive"
        )

    password = settings.mk_db_password
    assert password is not None
    engine = create_engine(
        URL.create(
            "postgresql+psycopg",
            username=settings.mk_db_user,
            password=password.get_secret_value(),
            host=settings.mk_db_host,
            port=settings.mk_db_port,
            database=settings.mk_db_name,
        ),
        pool_pre_ping=True,
        pool_size=_POOL_SIZE,
        max_overflow=_POOL_MAX_OVERFLOW,
        pool_recycle=_POOL_RECYCLE_SECONDS,
        pool_timeout=_POOL_TIMEOUT_SECONDS,
        connect_args={
            "connect_timeout": settings.mk_db_connect_timeout_seconds,
            "options": (
                "-c default_transaction_read_only=on "
                f"-c statement_timeout={settings.mk_db_statement_timeout_ms}"
            ),
            "sslmode": settings.mk_db_sslmode,
        },
    )
    event.listen(engine, "connect", _enforce_read_only)
    return MkDatabaseConnector(engine)


def _enforce_read_only(dbapi_connection: object, _: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    try:
        cursor.execute("SET default_transaction_read_only = on")
    finally:
        cursor.close()


def _safe_error_kind(error: DBAPIError) -> MkDatabaseErrorKind:
    original = error.orig
    sqlstate = getattr(original, "sqlstate", None)
    if sqlstate == "28P01":
        return MkDatabaseErrorKind.AUTHENTICATION
    if sqlstate in {"57014", "57P01", "57P02", "57P03"}:
        return MkDatabaseErrorKind.DATABASE_UNAVAILABLE
    if isinstance(original, (TimeoutError, ConnectionError)):
        return MkDatabaseErrorKind.TIMEOUT
    if error.connection_invalidated:
        return MkDatabaseErrorKind.DATABASE_UNAVAILABLE
    return MkDatabaseErrorKind.QUERY
