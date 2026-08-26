from __future__ import annotations

from datetime import date, datetime

import pytest

from supervisor_ai.infrastructure.external.mk.contracts import (
    MkAttendance,
    MkDialogSession,
    MkUser,
)
from supervisor_ai.infrastructure.external.mk.queries import (
    MkAttendanceRepository,
    MkDialogSessionRepository,
    MkQueryRepositories,
    MkUserRepository,
)
from tests.infrastructure.mk_query_fixtures import (
    ATTENDANCE_CLOSED_ROW,
    ATTENDANCE_OPEN_ROW,
    DIALOG_EVALUATED_ROW,
    DIALOG_OPERATOR_ROW,
    DIALOG_UNANSWERED_ROW,
    MK_USER_ROW,
)


class FakeResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def mappings(self) -> list[dict[str, object]]:
        return self.rows


class FakeConnection:
    def __init__(self, pages: list[list[dict[str, object]]]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def execute(self, statement, parameters) -> FakeResult:
        self.calls.append((str(statement), parameters))
        return FakeResult(self.pages.pop(0))


class FakeEngine:
    def __init__(self, *pages: list[dict[str, object]]) -> None:
        self.connection = FakeConnection(list(pages))
        self.connect_calls = 0

    def connect(self) -> FakeConnection:
        self.connect_calls += 1
        return self.connection


def test_attendance_query_uses_pk_cursor_period_and_explicit_columns() -> None:
    engine = FakeEngine([ATTENDANCE_CLOSED_ROW, ATTENDANCE_OPEN_ROW])
    repository = MkAttendanceRepository(engine)  # type: ignore[arg-type]

    result = repository.list_page(
        after_id=100,
        page_size=2,
        opened_from=date(2026, 8, 1),
        opened_through=date(2026, 8, 31),
    )

    assert [item.attendance_id for item in result] == [101, 102]
    assert result[0] == MkAttendance(
        attendance_id=101,
        protocol="2699.10180",
        customer_id=7001,
        opened_at=datetime(2026, 8, 20, 9, 10, 11),
        closed_at=datetime(2026, 8, 20, 10, 30, 45, 123000),
        opening_operator="operator.open",
        closing_operator="operator.close",
        process_id=44,
        subprocess_id=71,
        opening_classification_id=81,
        closing_classification_id=91,
        origin_id=9,
        status="closed",
        finalized="S",
        dialog_session_id=501,
    )
    assert result[1].closed_at is None
    sql, parameters = engine.connection.calls[0]
    assert "codatendimento > :after_id" in sql
    assert "ORDER BY codatendimento ASC" in sql
    assert "OFFSET" not in sql.upper()
    assert "SELECT *" not in sql.upper()
    assert parameters == {
        "after_id": 100,
        "page_size": 2,
        "opened_from": date(2026, 8, 1),
        "opened_through": date(2026, 8, 31),
    }


def test_dialog_query_preserves_naive_timestamps_and_null_score() -> None:
    engine = FakeEngine([DIALOG_EVALUATED_ROW, DIALOG_UNANSWERED_ROW])
    repository = MkDialogSessionRepository(engine)  # type: ignore[arg-type]

    result = repository.list_page(
        after_id=500,
        page_size=10,
        created_from=datetime(2026, 8, 20),
        created_through=datetime(2026, 8, 20, 23, 59, 59),
    )

    assert result[0] == MkDialogSession(
        dialog_session_id=501,
        protocol="2699.50010",
        score=5,
        created_at=datetime(2026, 8, 20, 9, 9, 30),
        human_service_started_at=datetime(2026, 8, 20, 9, 10),
        closed_at=datetime(2026, 8, 20, 10, 30),
        entered_queue_at=datetime(2026, 8, 20, 9, 9, 45),
        sector_id=10,
        integration_code="fixture-integration",
        channel_type="Whatsapp",
        person_id=7001,
    )
    assert result[1].score is None
    assert result[0].created_at.tzinfo is None
    sql, _ = engine.connection.calls[0]
    assert "cod_dialogosessao > :after_id" in sql
    assert "OFFSET" not in sql.upper()
    assert "SELECT *" not in sql.upper()


def test_dialog_operator_links_are_loaded_in_one_batched_query() -> None:
    engine = FakeEngine([DIALOG_OPERATOR_ROW])
    repository = MkDialogSessionRepository(engine)  # type: ignore[arg-type]

    result = repository.list_operator_links((501, 502))

    assert len(result) == 1
    assert result[0].dialog_session_id == 501
    assert result[0].user_id == 301
    assert engine.connect_calls == 1
    sql, parameters = engine.connection.calls[0]
    assert "coddialogosessao IN" in sql
    assert parameters == {"dialog_session_ids": (501, 502)}


def test_user_queries_support_cursor_and_batched_identity_resolution() -> None:
    engine = FakeEngine([MK_USER_ROW], [MK_USER_ROW])
    repository = MkUserRepository(engine)  # type: ignore[arg-type]

    page = repository.list_page(after_id=300, page_size=5)
    selected = repository.get_by_ids((301,))

    assert page == selected == (MkUser(301, "fixture.operator", "Operador Fictício"),)
    first_sql, first_parameters = engine.connection.calls[0]
    second_sql, second_parameters = engine.connection.calls[1]
    assert "usr_codigo > :after_id" in first_sql
    assert first_parameters == {"after_id": 300, "page_size": 5}
    assert "usr_codigo IN" in second_sql
    assert second_parameters == {"user_ids": (301,)}


def test_empty_batches_do_not_open_external_connections() -> None:
    engine = FakeEngine()
    dialogs = MkDialogSessionRepository(engine)  # type: ignore[arg-type]
    users = MkUserRepository(engine)  # type: ignore[arg-type]
    assert dialogs.list_operator_links(()) == ()
    assert users.get_by_ids(()) == ()
    assert engine.connect_calls == 0


@pytest.mark.parametrize("page_size", (0, 1001))
def test_page_size_is_bounded(page_size: int) -> None:
    repository = MkAttendanceRepository(FakeEngine())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="page_size"):
        repository.list_page(page_size=page_size)


def test_periods_and_source_timestamp_contract_are_validated() -> None:
    attendances = MkAttendanceRepository(FakeEngine())  # type: ignore[arg-type]
    dialogs = MkDialogSessionRepository(FakeEngine())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="period"):
        attendances.list_page(
            opened_from=date(2026, 8, 2), opened_through=date(2026, 8, 1)
        )
    with pytest.raises(ValueError, match="naive"):
        dialogs.list_page(
            created_from=datetime.fromisoformat("2026-08-01T00:00:00-03:00")
        )


def test_repository_bundle_reuses_one_external_engine() -> None:
    engine = FakeEngine()
    repositories = MkQueryRepositories.from_engine(engine)  # type: ignore[arg-type]
    assert repositories.attendances._engine is engine
    assert repositories.dialog_sessions._engine is engine
    assert repositories.users._engine is engine
