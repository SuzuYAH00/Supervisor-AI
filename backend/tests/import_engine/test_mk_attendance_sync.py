from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select

from supervisor_ai.application.mk_operational import (
    MK_SOURCE,
    MkSyncState,
    MkSyncStatus,
)
from supervisor_ai.import_engine.mk_attendance_sync import (
    MK_ATTENDANCE_ENTITY,
    MkAttendanceSyncAlreadyRunning,
    MkAttendanceSyncError,
    SyncMkAttendancesCommand,
    SyncMkAttendancesUseCase,
)
from supervisor_ai.infrastructure.external.mk import MkAttendance
from supervisor_ai.infrastructure.persistence.models import MkAttendanceMirrorRecord
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

NOW = datetime(2026, 8, 26, 12, tzinfo=UTC)


def mk_attendance(
    attendance_id: int,
    *,
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
    closing_operator: str | None = None,
    status: str = "open",
    finalized: str = "N",
) -> MkAttendance:
    return MkAttendance(
        attendance_id=attendance_id,
        protocol=f"2699.{attendance_id}0",
        customer_id=7001,
        opened_at=opened_at or datetime(2026, 7, 13, 11, 0, 22),
        closed_at=closed_at,
        opening_operator="9999",
        closing_operator=closing_operator,
        process_id=44,
        subprocess_id=71,
        opening_classification_id=81,
        closing_classification_id=91 if closed_at else None,
        origin_id=9,
        status=status,
        finalized=finalized,
        dialog_session_id=501,
    )


class FakeMkAttendanceRepository:
    def __init__(self, rows: tuple[MkAttendance, ...] = ()) -> None:
        self.rows = {row.attendance_id: row for row in rows}
        self.page_calls: list[dict[str, object]] = []
        self.id_calls: list[tuple[int, ...]] = []
        self.failure: Exception | None = None

    def list_page(
        self,
        *,
        after_id=None,
        page_size=100,
        opened_from=None,
        opened_through=None,
    ) -> tuple[MkAttendance, ...]:
        self.page_calls.append(
            {
                "after_id": after_id,
                "page_size": page_size,
                "opened_from": opened_from,
                "opened_through": opened_through,
            }
        )
        if self.failure is not None:
            raise self.failure
        rows = sorted(self.rows.values(), key=lambda row: row.attendance_id)
        return tuple(
            row
            for row in rows
            if (after_id is None or row.attendance_id > after_id)
            and (opened_from is None or row.opened_at.date() >= opened_from)
            and (opened_through is None or row.opened_at.date() <= opened_through)
        )[:page_size]

    def get_by_ids(self, attendance_ids: tuple[int, ...]) -> tuple[MkAttendance, ...]:
        self.id_calls.append(attendance_ids)
        if self.failure is not None:
            raise self.failure
        return tuple(
            self.rows[attendance_id]
            for attendance_id in attendance_ids
            if attendance_id in self.rows
        )


def use_case(repository, session_factory, *, factory=None):
    return SyncMkAttendancesUseCase(
        repository,
        factory or (lambda: SqlAlchemyUnitOfWork(session_factory)),
        clock=lambda: NOW,
        run_id_generator=lambda: "sync-run-fixture",
    )


def command(**changes: object) -> SyncMkAttendancesCommand:
    values: dict[str, object] = {
        "page_size": 2,
        "reconcile_open": False,
        "recent_reconciliation_days": None,
    }
    values.update(changes)
    return SyncMkAttendancesCommand(**values)  # type: ignore[arg-type]


def test_new_records_page_by_pk_and_persist_cursor_and_audit(session_factory) -> None:
    repository = FakeMkAttendanceRepository(
        tuple(mk_attendance(index) for index in range(1, 6))
    )
    result = use_case(repository, session_factory).execute(command())

    assert result.inserted == 5
    assert result.cursor_start is None
    assert result.cursor_end == 5
    assert [call["after_id"] for call in repository.page_calls] == [None, 2, 4]
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        state = unit_of_work.mk_sync.get_state(
            source=MK_SOURCE, entity_type=MK_ATTENDANCE_ENTITY
        )
        run = unit_of_work.mk_sync.get_run("sync-run-fixture")
        assert state is not None
        assert state.last_pk == 5
        assert state.status is MkSyncStatus.SUCCEEDED
        assert state.last_success_at == NOW
        assert run is not None
        assert run.inserted == 5
        assert run.final_cursor == 5
        assert run.status is MkSyncStatus.SUCCEEDED


def test_empty_sync_is_audited_without_advancing_cursor(session_factory) -> None:
    result = use_case(FakeMkAttendanceRepository(), session_factory).execute(command())
    assert result.cursor_start is result.cursor_end is None
    assert result.inserted == result.updated == result.unchanged == 0
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.mk_sync.get_run("sync-run-fixture") is not None


def test_reconciliation_is_idempotent_and_closes_open_attendance(
    session_factory,
) -> None:
    repository = FakeMkAttendanceRepository((mk_attendance(1),))
    first = use_case(repository, session_factory).execute(command())
    assert first.inserted == 1

    second = SyncMkAttendancesUseCase(
        repository,
        lambda: SqlAlchemyUnitOfWork(session_factory),
        clock=lambda: NOW,
        run_id_generator=lambda: "sync-run-second",
    ).execute(command(reconcile_open=True))
    assert second.unchanged == 1
    assert repository.id_calls == [(1,)]

    repository.rows[1] = mk_attendance(
        1,
        closed_at=datetime(2026, 7, 13, 12),
        closing_operator="1788",
        status="closed",
        finalized="S",
    )
    third = SyncMkAttendancesUseCase(
        repository,
        lambda: SqlAlchemyUnitOfWork(session_factory),
        clock=lambda: NOW,
        run_id_generator=lambda: "sync-run-third",
    ).execute(command(reconcile_open=True))
    assert third.updated == 1
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        persisted = unit_of_work.mk_attendances.get_by_external_id("1")
        assert persisted is not None
        assert persisted.closed_at == datetime(2026, 7, 13, 15, tzinfo=UTC)
        assert persisted.closing_operator_external_id == "1788"
        assert persisted.status == "closed"
        assert unit_of_work.mk_attendances.list_open() == ()


def test_recent_window_reconciles_mutation_without_deleting_missing_rows(
    session_factory,
) -> None:
    repository = FakeMkAttendanceRepository(
        (
            mk_attendance(
                1,
                opened_at=datetime(2026, 8, 25, 10),
                closed_at=datetime(2026, 8, 25, 11),
                status="closed",
                finalized="S",
            ),
            mk_attendance(2),
        )
    )
    use_case(repository, session_factory).execute(command())
    repository.rows[1] = replace(repository.rows[1], status="corrected")
    repository.rows.pop(2)

    result = SyncMkAttendancesUseCase(
        repository,
        lambda: SqlAlchemyUnitOfWork(session_factory),
        clock=lambda: NOW,
        run_id_generator=lambda: "sync-run-recent",
    ).execute(
        command(
            reconcile_open=False,
            recent_reconciliation_days=7,
        )
    )
    assert result.updated == 1
    assert repository.page_calls[-1]["opened_from"] == date(2026, 8, 19)
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.mk_attendances.get_by_external_id("1").status == (  # type: ignore[union-attr]
            "corrected"
        )
        assert unit_of_work.mk_attendances.get_by_external_id("2") is not None


class _FailingAttendanceRepository:
    def __init__(self, delegate, fail_at: int) -> None:
        self.delegate = delegate
        self.fail_at = fail_at
        self.calls = 0

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def upsert(self, item):
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("local fixture failure password=secret")
        return self.delegate.upsert(item)


class _FailingUnitOfWork(SqlAlchemyUnitOfWork):
    fail_enabled = True

    def __enter__(self):
        value = super().__enter__()
        if self.fail_enabled:
            self.mk_attendances = _FailingAttendanceRepository(self.mk_attendances, 7)
        return value


def test_local_failure_rolls_back_batch_and_cursor_then_retry_succeeds(
    session_factory,
) -> None:
    repository = FakeMkAttendanceRepository(
        tuple(mk_attendance(index) for index in range(1, 11))
    )
    def factory() -> _FailingUnitOfWork:
        return _FailingUnitOfWork(session_factory)
    sync = use_case(repository, session_factory, factory=factory)
    with pytest.raises(MkAttendanceSyncError):
        sync.execute(command(page_size=10))

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        state = unit_of_work.mk_sync.get_state(
            source=MK_SOURCE, entity_type=MK_ATTENDANCE_ENTITY
        )
        assert state is not None
        assert state.last_pk is None
        assert state.status is MkSyncStatus.FAILED
        failed_run = unit_of_work.mk_sync.get_run("sync-run-fixture")
        assert failed_run is not None
        assert failed_run.status is MkSyncStatus.FAILED
        assert "secret" not in (failed_run.error or "")
    with session_factory() as session:
        assert (
            session.scalar(select(func.count()).select_from(MkAttendanceMirrorRecord))
            == 0
        )

    _FailingUnitOfWork.fail_enabled = False
    retry = SyncMkAttendancesUseCase(
        repository,
        factory,
        clock=lambda: NOW,
        run_id_generator=lambda: "sync-run-retry",
    ).execute(command(page_size=10))
    assert retry.inserted == 10
    assert retry.cursor_end == 10


def test_external_failure_records_failure_without_advancing_cursor(
    session_factory,
) -> None:
    repository = FakeMkAttendanceRepository()
    repository.failure = TimeoutError("external timeout password=secret")
    with pytest.raises(MkAttendanceSyncError):
        use_case(repository, session_factory).execute(command())

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        state = unit_of_work.mk_sync.get_state(
            source=MK_SOURCE, entity_type=MK_ATTENDANCE_ENTITY
        )
        assert state is not None
        assert state.last_pk is None
        assert state.status is MkSyncStatus.FAILED
        assert "secret" not in (state.last_error or "")


def test_running_state_prevents_concurrent_sync(session_factory) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.mk_sync.save_state(
            MkSyncState(
                source=MK_SOURCE,
                entity_type=MK_ATTENDANCE_ENTITY,
                last_pk=50,
                last_success_at=NOW,
                last_attempt_at=NOW,
                status=MkSyncStatus.RUNNING,
                last_error=None,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        unit_of_work.commit()
    repository = FakeMkAttendanceRepository()
    with pytest.raises(MkAttendanceSyncAlreadyRunning):
        use_case(repository, session_factory).execute(command())
    assert repository.page_calls == []


def test_real_sync_path_normalizes_timezone_dialog_and_unknown_operator(
    session_factory,
) -> None:
    repository = FakeMkAttendanceRepository((mk_attendance(1),))
    use_case(repository, session_factory).execute(command())
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        persisted = unit_of_work.mk_attendances.get_by_external_id("1")
        assert persisted is not None
        assert persisted.opened_at == datetime(2026, 7, 13, 14, 0, 22, tzinfo=UTC)
        assert persisted.opening_operator_external_id == "9999"
        assert persisted.mk_dialog_session_external_id == "501"
