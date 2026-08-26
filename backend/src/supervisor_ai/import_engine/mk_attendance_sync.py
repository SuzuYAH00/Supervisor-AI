from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from supervisor_ai.application.mk_operational import (
    MK_SOURCE,
    MkAttendanceMirror,
    MkSyncRun,
    MkSyncState,
    MkSyncStatus,
    MkUpsertOutcome,
)
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.infrastructure.external.mk.contracts import (
    MAX_MK_PAGE_SIZE,
    MkAttendance,
    MkAttendanceQuery,
)
from supervisor_ai.infrastructure.external.mk.database import MK_SOURCE_TIMEZONE
from supervisor_ai.infrastructure.external.mk.time import mk_local_datetime_to_utc

MK_ATTENDANCE_ENTITY = "attendance"
DEFAULT_MK_ATTENDANCE_PAGE_SIZE = 500
DEFAULT_RECENT_RECONCILIATION_DAYS = 7


class MkAttendanceSyncError(RuntimeError):
    pass


class MkAttendanceSyncAlreadyRunning(MkAttendanceSyncError):
    pass


class MkAttendanceSyncConcurrentCursor(MkAttendanceSyncError):
    pass


class MkAttendanceMappingError(MkAttendanceSyncError):
    pass


@dataclass(frozen=True, slots=True)
class SyncMkAttendancesCommand:
    page_size: int = DEFAULT_MK_ATTENDANCE_PAGE_SIZE
    reconcile_open: bool = True
    recent_reconciliation_days: int | None = DEFAULT_RECENT_RECONCILIATION_DAYS
    reconcile_from: date | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.page_size <= MAX_MK_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_MK_PAGE_SIZE}")
        if self.recent_reconciliation_days is not None and not (
            0 <= self.recent_reconciliation_days <= 90
        ):
            raise ValueError("recent_reconciliation_days must be between 0 and 90")


@dataclass(frozen=True, slots=True)
class SyncMkAttendancesResult:
    run_id: str
    cursor_start: int | None
    cursor_end: int | None
    inserted: int
    updated: int
    unchanged: int
    rejected: int
    status: MkSyncStatus


@dataclass(slots=True)
class _Counters:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0

    def add(self, outcomes: tuple[MkUpsertOutcome, ...]) -> None:
        self.inserted += outcomes.count(MkUpsertOutcome.INSERTED)
        self.updated += outcomes.count(MkUpsertOutcome.UPDATED)
        self.unchanged += outcomes.count(MkUpsertOutcome.UNCHANGED)


class SyncMkAttendancesUseCase:
    """Sincroniza fatos MK sem projetar regras ou entidades consolidadas."""

    def __init__(
        self,
        external_repository: MkAttendanceQuery,
        unit_of_work_factory: UnitOfWorkFactory,
        *,
        clock: Callable[[], datetime] | None = None,
        run_id_generator: Callable[[], str] | None = None,
    ) -> None:
        self._external_repository = external_repository
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock or (lambda: datetime.now(UTC))
        self._run_id_generator = run_id_generator or (lambda: str(uuid4()))

    def execute(self, command: SyncMkAttendancesCommand) -> SyncMkAttendancesResult:
        started_at = self._now()
        run_id = self._run_id_generator()
        state = self._start(run_id, started_at)
        cursor_start = state.last_pk
        cursor = cursor_start
        counters = _Counters()

        try:
            cursor = self._sync_new(command.page_size, cursor, run_id, counters)
            if command.reconcile_open and cursor_start is not None:
                self._reconcile_open(
                    command.page_size,
                    cursor_start,
                    run_id,
                    counters,
                )
            reconcile_from = self._reconciliation_start(command)
            if reconcile_from is not None and cursor_start is not None:
                self._reconcile_recent(
                    command.page_size,
                    reconcile_from,
                    cursor_start,
                    run_id,
                    counters,
                )
            self._finish(run_id, cursor, counters)
        except MkAttendanceSyncAlreadyRunning:
            raise
        except Exception as error:
            self._fail(run_id, counters, error)
            if isinstance(error, MkAttendanceSyncError):
                raise
            raise MkAttendanceSyncError("MK attendance sync failed") from error

        return SyncMkAttendancesResult(
            run_id=run_id,
            cursor_start=cursor_start,
            cursor_end=cursor,
            inserted=counters.inserted,
            updated=counters.updated,
            unchanged=counters.unchanged,
            rejected=counters.rejected,
            status=MkSyncStatus.SUCCEEDED,
        )

    def _start(self, run_id: str, started_at: datetime) -> MkSyncState:
        with self._unit_of_work_factory() as unit_of_work:
            state = unit_of_work.mk_sync.get_state_for_update(
                source=MK_SOURCE, entity_type=MK_ATTENDANCE_ENTITY
            )
            if state is not None and state.status is MkSyncStatus.RUNNING:
                raise MkAttendanceSyncAlreadyRunning(
                    "MK attendance sync is already running"
                )
            if state is None:
                state = MkSyncState(
                    source=MK_SOURCE,
                    entity_type=MK_ATTENDANCE_ENTITY,
                    last_pk=None,
                    last_success_at=None,
                    last_attempt_at=started_at,
                    status=MkSyncStatus.RUNNING,
                    last_error=None,
                    created_at=started_at,
                    updated_at=started_at,
                )
            else:
                state = replace(
                    state,
                    last_attempt_at=started_at,
                    status=MkSyncStatus.RUNNING,
                    last_error=None,
                    updated_at=started_at,
                )
            unit_of_work.mk_sync.save_state(state)
            unit_of_work.mk_sync.add_run(
                MkSyncRun(
                    id=run_id,
                    source=MK_SOURCE,
                    entity_type=MK_ATTENDANCE_ENTITY,
                    initial_cursor=state.last_pk,
                    final_cursor=state.last_pk,
                    inserted=0,
                    updated=0,
                    unchanged=0,
                    rejected=0,
                    status=MkSyncStatus.RUNNING,
                    started_at=started_at,
                    finished_at=None,
                    error=None,
                    created_at=started_at,
                )
            )
            unit_of_work.commit()
            return state

    def _sync_new(
        self,
        page_size: int,
        cursor: int | None,
        run_id: str,
        counters: _Counters,
    ) -> int | None:
        while True:
            rows = self._external_repository.list_page(
                after_id=cursor,
                page_size=page_size,
            )
            if not rows:
                return cursor
            seen_at = self._now()
            items = self._map_rows(rows, seen_at, counters)
            next_cursor = max(row.attendance_id for row in rows)
            outcomes = self._persist_batch(
                items,
                run_id=run_id,
                counters=counters,
                expected_cursor=cursor,
                next_cursor=next_cursor,
            )
            counters.add(outcomes)
            cursor = next_cursor
            if len(rows) < page_size:
                return cursor

    def _reconcile_open(
        self,
        page_size: int,
        existing_through: int,
        run_id: str,
        counters: _Counters,
    ) -> None:
        after_external_id: str | None = None
        while True:
            with self._unit_of_work_factory() as unit_of_work:
                open_items = unit_of_work.mk_attendances.list_open(
                    after_external_id=after_external_id,
                    limit=page_size,
                )
            if not open_items:
                return
            external_ids = tuple(
                int(item.external_id)
                for item in open_items
                if int(item.external_id) <= existing_through
            )
            rows = self._external_repository.get_by_ids(external_ids)
            items = self._map_rows(rows, self._now(), counters)
            outcomes = self._persist_reconciliation(items, run_id, counters)
            counters.add(outcomes)
            after_external_id = open_items[-1].external_id
            if len(open_items) < page_size:
                return

    def _reconcile_recent(
        self,
        page_size: int,
        opened_from: date,
        existing_through: int,
        run_id: str,
        counters: _Counters,
    ) -> None:
        cursor: int | None = None
        while True:
            page = self._external_repository.list_page(
                after_id=cursor,
                page_size=page_size,
                opened_from=opened_from,
            )
            if not page:
                return
            rows = tuple(row for row in page if row.attendance_id <= existing_through)
            items = self._map_rows(rows, self._now(), counters)
            outcomes = self._persist_reconciliation(items, run_id, counters)
            counters.add(outcomes)
            cursor = max(row.attendance_id for row in page)
            if len(page) < page_size or cursor >= existing_through:
                return

    def _persist_batch(
        self,
        items: tuple[MkAttendanceMirror, ...],
        *,
        run_id: str,
        counters: _Counters,
        expected_cursor: int | None,
        next_cursor: int,
    ) -> tuple[MkUpsertOutcome, ...]:
        with self._unit_of_work_factory() as unit_of_work:
            state = self._running_state_for_update(unit_of_work)
            if state.last_pk != expected_cursor:
                raise MkAttendanceSyncConcurrentCursor(
                    "MK attendance cursor changed during sync"
                )
            outcomes = tuple(unit_of_work.mk_attendances.upsert(item) for item in items)
            now = self._now()
            projected = _project_counters(counters, outcomes)
            unit_of_work.mk_sync.save_state(
                replace(state, last_pk=next_cursor, updated_at=now)
            )
            self._update_running_run(unit_of_work, run_id, next_cursor, projected)
            unit_of_work.commit()
            return outcomes

    def _persist_reconciliation(
        self,
        items: tuple[MkAttendanceMirror, ...],
        run_id: str,
        counters: _Counters,
    ) -> tuple[MkUpsertOutcome, ...]:
        if not items:
            return ()
        with self._unit_of_work_factory() as unit_of_work:
            state = self._running_state_for_update(unit_of_work)
            outcomes = tuple(unit_of_work.mk_attendances.upsert(item) for item in items)
            projected = _project_counters(counters, outcomes)
            self._update_running_run(unit_of_work, run_id, state.last_pk, projected)
            unit_of_work.commit()
            return outcomes

    def _finish(self, run_id: str, cursor: int | None, counters: _Counters) -> None:
        finished_at = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            state = self._running_state_for_update(unit_of_work)
            unit_of_work.mk_sync.save_state(
                replace(
                    state,
                    last_pk=cursor,
                    last_success_at=finished_at,
                    status=MkSyncStatus.SUCCEEDED,
                    last_error=None,
                    updated_at=finished_at,
                )
            )
            run = _require_run(unit_of_work, run_id)
            unit_of_work.mk_sync.update_run(
                replace(
                    run,
                    final_cursor=cursor,
                    inserted=counters.inserted,
                    updated=counters.updated,
                    unchanged=counters.unchanged,
                    rejected=counters.rejected,
                    status=MkSyncStatus.SUCCEEDED,
                    finished_at=finished_at,
                    error=None,
                )
            )
            unit_of_work.commit()

    def _fail(self, run_id: str, counters: _Counters, error: Exception) -> None:
        failed_at = self._now()
        safe_error = f"{type(error).__name__}: {error}"
        try:
            with self._unit_of_work_factory() as unit_of_work:
                state = unit_of_work.mk_sync.get_state_for_update(
                    source=MK_SOURCE, entity_type=MK_ATTENDANCE_ENTITY
                )
                if state is not None:
                    unit_of_work.mk_sync.save_state(
                        replace(
                            state,
                            status=MkSyncStatus.FAILED,
                            last_error=safe_error,
                            updated_at=failed_at,
                        )
                    )
                run = unit_of_work.mk_sync.get_run(run_id)
                if run is not None:
                    unit_of_work.mk_sync.update_run(
                        replace(
                            run,
                            inserted=counters.inserted,
                            updated=counters.updated,
                            unchanged=counters.unchanged,
                            rejected=counters.rejected,
                            status=MkSyncStatus.FAILED,
                            finished_at=failed_at,
                            error=safe_error,
                        )
                    )
                unit_of_work.commit()
        except Exception:
            # A falha de auditoria não pode ocultar a causa original.
            return

    def _running_state_for_update(self, unit_of_work) -> MkSyncState:
        state = unit_of_work.mk_sync.get_state_for_update(
            source=MK_SOURCE, entity_type=MK_ATTENDANCE_ENTITY
        )
        if state is None or state.status is not MkSyncStatus.RUNNING:
            raise MkAttendanceSyncConcurrentCursor(
                "MK attendance sync no longer owns the sync state"
            )
        return state

    def _update_running_run(
        self,
        unit_of_work,
        run_id: str,
        cursor: int | None,
        counters: _Counters,
    ) -> None:
        run = _require_run(unit_of_work, run_id)
        unit_of_work.mk_sync.update_run(
            replace(
                run,
                final_cursor=cursor,
                inserted=counters.inserted,
                updated=counters.updated,
                unchanged=counters.unchanged,
                rejected=counters.rejected,
            )
        )

    def _map_rows(
        self,
        rows: tuple[MkAttendance, ...],
        seen_at: datetime,
        counters: _Counters,
    ) -> tuple[MkAttendanceMirror, ...]:
        try:
            return tuple(_map_attendance(row, seen_at) for row in rows)
        except (TypeError, ValueError) as error:
            counters.rejected += 1
            raise MkAttendanceMappingError(
                "MK attendance row violates the sync contract"
            ) from error

    def _reconciliation_start(self, command: SyncMkAttendancesCommand) -> date | None:
        if command.reconcile_from is not None:
            return command.reconcile_from
        if command.recent_reconciliation_days is None:
            return None
        local_today = self._now().astimezone(MK_SOURCE_TIMEZONE).date()
        return local_today - timedelta(days=command.recent_reconciliation_days)

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("sync clock must return a timezone-aware datetime")
        return value.astimezone(UTC)


def _map_attendance(item: MkAttendance, seen_at: datetime) -> MkAttendanceMirror:
    opened_at = mk_local_datetime_to_utc(item.opened_at)
    if opened_at is None:
        raise ValueError("MK attendance opened_at is required")
    return MkAttendanceMirror(
        external_id=str(item.attendance_id),
        protocol=item.protocol,
        customer_external_id=_optional_text(item.customer_id),
        opened_at=opened_at,
        closed_at=mk_local_datetime_to_utc(item.closed_at),
        opening_operator_external_id=_optional_text(item.opening_operator),
        closing_operator_external_id=_optional_text(item.closing_operator),
        process_external_id=_optional_text(item.process_id),
        subprocess_external_id=_optional_text(item.subprocess_id),
        opening_classification_external_id=_optional_text(
            item.opening_classification_id
        ),
        closing_classification_external_id=_optional_text(
            item.closing_classification_id
        ),
        origin_external_id=_optional_text(item.origin_id),
        status=item.status,
        is_finalized=_finalized(item.finalized),
        mk_dialog_session_external_id=_optional_text(item.dialog_session_id),
        source_first_seen_at=seen_at,
        source_last_seen_at=seen_at,
        local_created_at=seen_at,
        local_updated_at=seen_at,
    )


def _optional_text(value: object | None) -> str | None:
    return None if value is None else str(value)


def _finalized(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if normalized in {"1", "s", "sim", "true"}:
        return True
    if normalized in {"0", "n", "nao", "não", "false"}:
        return False
    raise ValueError("unsupported MK finalized value")


def _project_counters(
    counters: _Counters, outcomes: tuple[MkUpsertOutcome, ...]
) -> _Counters:
    projected = _Counters(
        counters.inserted,
        counters.updated,
        counters.unchanged,
        counters.rejected,
    )
    projected.add(outcomes)
    return projected


def _require_run(unit_of_work, run_id: str) -> MkSyncRun:
    run = unit_of_work.mk_sync.get_run(run_id)
    if run is None:
        raise MkAttendanceSyncError("MK attendance sync run was not found")
    return run
