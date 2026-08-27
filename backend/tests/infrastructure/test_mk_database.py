from __future__ import annotations

from contextlib import nullcontext

import pytest
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError

from supervisor_ai.core.config import MkDatabaseSettings
from supervisor_ai.infrastructure.external.mk import database
from supervisor_ai.infrastructure.external.mk.database import (
    MK_SOURCE_TIMEZONE,
    MkDatabaseConfigurationError,
    MkDatabaseConnector,
    MkDatabaseErrorKind,
    MkDatabaseStatus,
    _enforce_read_only,
    create_mk_database_connector,
)


class FakeCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.closed = False

    def execute(self, statement: str) -> None:
        self.statements.append(statement)

    def close(self) -> None:
        self.closed = True


class FakeDbapiConnection:
    def __init__(self) -> None:
        self.value = FakeCursor()

    def cursor(self) -> FakeCursor:
        return self.value


class FakeConnection:
    def __init__(self, *, read_only: str = "on") -> None:
        self.read_only = read_only

    def scalar(self, statement) -> int | str:
        sql = str(statement)
        return 1 if sql == "SELECT 1" else self.read_only


class FakeEngine:
    def __init__(self, connection=None, error: Exception | None = None) -> None:
        self.connection = connection or FakeConnection()
        self.error = error
        self.disposed = False

    def connect(self):
        if self.error is not None:
            raise self.error
        return nullcontext(self.connection)

    def dispose(self) -> None:
        self.disposed = True


def settings(**overrides) -> MkDatabaseSettings:
    values = {
        "mk_db_host": "mk-db.invalid",
        "mk_db_name": "mk",
        "mk_db_user": "reader",
        "mk_db_password": SecretStr("not-a-real-password"),
        "mk_db_sslmode": "require",
    }
    values.update(overrides)
    return MkDatabaseSettings(**values)


def test_tls_is_required_by_default_and_non_tls_requires_explicit_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MK_DB_SSLMODE", raising=False)
    assert MkDatabaseSettings().mk_db_sslmode == "require"
    assert MkDatabaseSettings(mk_db_sslmode="disable").mk_db_sslmode == "disable"


def test_missing_configuration_is_optional_and_partial_configuration_is_safe() -> None:
    empty = MkDatabaseSettings(
        mk_db_host=None,
        mk_db_name=None,
        mk_db_user=None,
        mk_db_password=None,
    )
    assert create_mk_database_connector(empty) is None
    with pytest.raises(
        MkDatabaseConfigurationError,
        match="configuration is incomplete",
    ) as captured:
        create_mk_database_connector(
            MkDatabaseSettings(
                mk_db_host="host-only",
                mk_db_name=None,
                mk_db_user=None,
                mk_db_password=None,
            )
        )
    assert "host-only" not in str(captured.value)


def test_connector_builds_isolated_engine_with_conservative_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    engine = FakeEngine()

    def create_engine(url, **kwargs):
        captured.update(url=url, **kwargs)
        return engine

    monkeypatch.setattr(database, "create_engine", create_engine)
    monkeypatch.setattr(database.event, "listen", lambda *args: None)
    connector = create_mk_database_connector(
        settings(
            mk_db_connect_timeout_seconds=7,
            mk_db_statement_timeout_ms=12_000,
        )
    )
    assert connector is not None
    url = captured["url"]
    assert url.database == "mk"
    assert url.drivername == "postgresql+psycopg"
    assert "not-a-real-password" not in str(url)
    assert captured["pool_pre_ping"] is True
    assert captured["pool_size"] == 2
    assert captured["max_overflow"] == 0
    assert captured["pool_recycle"] == 300
    assert captured["pool_timeout"] == 5
    assert captured["connect_args"] == {
        "connect_timeout": 7,
        "options": (
            "-c default_transaction_read_only=on -c statement_timeout=12000"
        ),
        "sslmode": "require",
    }
    connector.dispose()
    assert engine.disposed


def test_read_only_is_enforced_on_every_new_dbapi_connection() -> None:
    connection = FakeDbapiConnection()
    _enforce_read_only(connection, object())
    assert connection.value.statements == ["SET default_transaction_read_only = on"]
    assert connection.value.closed


def test_health_check_confirms_connectivity_and_read_only() -> None:
    result = MkDatabaseConnector(FakeEngine()).check_health()  # type: ignore[arg-type]
    assert result.status is MkDatabaseStatus.AVAILABLE
    assert result.read_only
    assert result.error_kind is None


def test_health_check_rejects_connection_that_is_not_read_only() -> None:
    engine = FakeEngine(FakeConnection(read_only="off"))
    result = MkDatabaseConnector(engine).check_health()  # type: ignore[arg-type]
    assert result.status is MkDatabaseStatus.UNAVAILABLE
    assert not result.read_only
    assert result.error_kind is MkDatabaseErrorKind.QUERY


def test_health_error_is_sanitized() -> None:
    secret = "postgresql://reader:secret@mk-db.invalid/mk"
    error = OperationalError(
        "SELECT 1",
        {},
        TimeoutError(secret),
        connection_invalidated=False,
    )
    result = MkDatabaseConnector(FakeEngine(error=error)).check_health()  # type: ignore[arg-type]
    assert result.status is MkDatabaseStatus.UNAVAILABLE
    assert result.read_only is None
    assert result.error_kind is MkDatabaseErrorKind.TIMEOUT
    assert secret not in repr(result)


def test_source_timezone_is_centralized() -> None:
    assert MK_SOURCE_TIMEZONE.key == "America/Fortaleza"
