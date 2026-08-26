import re
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from supervisor_ai.application.mk_operational import (
    MkAttendanceMirror,
    MkBotConversationMirror,
    MkSyncRun,
    MkSyncState,
    MkSyncStatus,
    MkUpsertOutcome,
)
from supervisor_ai.infrastructure.persistence.models import (
    MkAttendanceMirrorRecord,
    MkBotConversationMirrorRecord,
    MkSyncRunRecord,
    MkSyncStateRecord,
)

_ATTENDANCE_FACT_FIELDS = (
    "protocol",
    "customer_external_id",
    "opened_at",
    "closed_at",
    "opening_operator_external_id",
    "closing_operator_external_id",
    "process_external_id",
    "subprocess_external_id",
    "opening_classification_external_id",
    "closing_classification_external_id",
    "origin_external_id",
    "status",
    "is_finalized",
    "mk_dialog_session_external_id",
)
_CONVERSATION_FACT_FIELDS = (
    "protocol",
    "person_external_id",
    "integration_external_reference",
    "conversation_type",
    "sector_external_id",
    "created_at",
    "human_service_started_at",
    "queue_entered_at",
    "closed_at",
    "score",
    "final_operator_external_id",
)


def sanitize_mk_sync_error(value: str | None) -> str | None:
    if value is None:
        return None
    sanitized = re.sub(
        r"(?i)(password|token|authorization)=?[^\s,;]+", r"\1=[REDACTED]", value
    )
    sanitized = re.sub(
        r"(?i)(postgres(?:ql)?://[^:@/\s]+):[^@/\s]+@", r"\1:[REDACTED]@", sanitized
    )
    return sanitized[:1000]


class SqlAlchemyMkAttendanceMirrorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_external_id(self, external_id: str) -> MkAttendanceMirror | None:
        record = self.session.get(MkAttendanceMirrorRecord, external_id)
        return None if record is None else _attendance_from_record(record)

    def upsert(self, item: MkAttendanceMirror) -> MkUpsertOutcome:
        record = self.session.get(MkAttendanceMirrorRecord, item.external_id)
        if record is None:
            self.session.add(_attendance_to_record(item))
            self.session.flush()
            return MkUpsertOutcome.INSERTED

        changed = any(
            getattr(record, name) != getattr(item, name)
            for name in _ATTENDANCE_FACT_FIELDS
        )
        for name in _ATTENDANCE_FACT_FIELDS:
            setattr(record, name, getattr(item, name))
        record.source_first_seen_at = min(
            record.source_first_seen_at, item.source_first_seen_at
        )
        record.source_last_seen_at = max(
            record.source_last_seen_at, item.source_last_seen_at
        )
        if changed:
            record.local_updated_at = item.local_updated_at
        self.session.flush()
        return MkUpsertOutcome.UPDATED if changed else MkUpsertOutcome.UNCHANGED

    def list_open(
        self, *, after_external_id: str | None = None, limit: int = 1000
    ) -> tuple[MkAttendanceMirror, ...]:
        _validate_limit(limit)
        query = select(MkAttendanceMirrorRecord).where(
            MkAttendanceMirrorRecord.closed_at.is_(None)
        )
        if after_external_id is not None:
            query = query.where(
                MkAttendanceMirrorRecord.external_id > after_external_id
            )
        records = self.session.scalars(
            query.order_by(MkAttendanceMirrorRecord.external_id).limit(limit)
        )
        return tuple(_attendance_from_record(record) for record in records)

    def list_by_dialog_session_external_id(
        self, external_id: str
    ) -> tuple[MkAttendanceMirror, ...]:
        records = self.session.scalars(
            select(MkAttendanceMirrorRecord)
            .where(
                MkAttendanceMirrorRecord.mk_dialog_session_external_id == external_id
            )
            .order_by(MkAttendanceMirrorRecord.external_id)
        )
        return tuple(_attendance_from_record(record) for record in records)


class SqlAlchemyMkBotConversationMirrorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_external_id(self, external_id: str) -> MkBotConversationMirror | None:
        record = self.session.get(MkBotConversationMirrorRecord, external_id)
        return None if record is None else _conversation_from_record(record)

    def upsert(self, item: MkBotConversationMirror) -> MkUpsertOutcome:
        record = self.session.get(MkBotConversationMirrorRecord, item.external_id)
        if record is None:
            self.session.add(_conversation_to_record(item))
            self.session.flush()
            return MkUpsertOutcome.INSERTED

        changed = any(
            getattr(record, name) != getattr(item, name)
            for name in _CONVERSATION_FACT_FIELDS
        )
        for name in _CONVERSATION_FACT_FIELDS:
            setattr(record, name, getattr(item, name))
        record.source_first_seen_at = min(
            record.source_first_seen_at, item.source_first_seen_at
        )
        record.source_last_seen_at = max(
            record.source_last_seen_at, item.source_last_seen_at
        )
        if changed:
            record.local_updated_at = item.local_updated_at
        self.session.flush()
        return MkUpsertOutcome.UPDATED if changed else MkUpsertOutcome.UNCHANGED

    def list_open(self, *, limit: int = 1000) -> tuple[MkBotConversationMirror, ...]:
        _validate_limit(limit)
        records = self.session.scalars(
            select(MkBotConversationMirrorRecord)
            .where(MkBotConversationMirrorRecord.closed_at.is_(None))
            .order_by(MkBotConversationMirrorRecord.external_id)
            .limit(limit)
        )
        return tuple(_conversation_from_record(record) for record in records)


class SqlAlchemyMkSyncRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_state(self, *, source: str, entity_type: str) -> MkSyncState | None:
        record = self.session.get(MkSyncStateRecord, (source, entity_type))
        return None if record is None else _state_from_record(record)

    def get_state_for_update(
        self, *, source: str, entity_type: str
    ) -> MkSyncState | None:
        record = self.session.scalar(
            select(MkSyncStateRecord)
            .where(
                MkSyncStateRecord.source == source,
                MkSyncStateRecord.entity_type == entity_type,
            )
            .with_for_update()
        )
        return None if record is None else _state_from_record(record)

    def save_state(self, state: MkSyncState) -> None:
        state = replace(state, last_error=sanitize_mk_sync_error(state.last_error))
        record = self.session.get(MkSyncStateRecord, (state.source, state.entity_type))
        if record is None:
            self.session.add(_state_to_record(state))
        else:
            for name in (
                "last_pk",
                "last_success_at",
                "last_attempt_at",
                "status",
                "last_error",
                "updated_at",
            ):
                value = getattr(state, name)
                setattr(
                    record,
                    name,
                    value.value if isinstance(value, MkSyncStatus) else value,
                )
        self.session.flush()

    def add_run(self, run: MkSyncRun) -> None:
        self.session.add(
            _run_to_record(replace(run, error=sanitize_mk_sync_error(run.error)))
        )
        self.session.flush()

    def update_run(self, run: MkSyncRun) -> None:
        record = self.session.get(MkSyncRunRecord, run.id)
        if record is None:
            raise LookupError(f"MK sync run {run.id!r} was not found")
        sanitized = replace(run, error=sanitize_mk_sync_error(run.error))
        for name in (
            "final_cursor",
            "inserted",
            "updated",
            "unchanged",
            "rejected",
            "status",
            "finished_at",
            "error",
        ):
            value = getattr(sanitized, name)
            setattr(
                record, name, value.value if isinstance(value, MkSyncStatus) else value
            )
        self.session.flush()

    def get_run(self, run_id: str) -> MkSyncRun | None:
        record = self.session.get(MkSyncRunRecord, run_id)
        return None if record is None else _run_from_record(record)


def _attendance_to_record(item: MkAttendanceMirror) -> MkAttendanceMirrorRecord:
    return MkAttendanceMirrorRecord(
        **{name: getattr(item, name) for name in item.__dataclass_fields__}
    )


def _attendance_from_record(record: MkAttendanceMirrorRecord) -> MkAttendanceMirror:
    return MkAttendanceMirror(
        **{
            name: getattr(record, name)
            for name in MkAttendanceMirror.__dataclass_fields__
        }
    )


def _conversation_to_record(
    item: MkBotConversationMirror,
) -> MkBotConversationMirrorRecord:
    return MkBotConversationMirrorRecord(
        **{name: getattr(item, name) for name in item.__dataclass_fields__}
    )


def _conversation_from_record(
    record: MkBotConversationMirrorRecord,
) -> MkBotConversationMirror:
    return MkBotConversationMirror(
        **{
            name: getattr(record, name)
            for name in MkBotConversationMirror.__dataclass_fields__
        }
    )


def _state_to_record(item: MkSyncState) -> MkSyncStateRecord:
    values = {name: getattr(item, name) for name in item.__dataclass_fields__}
    values["status"] = item.status.value
    return MkSyncStateRecord(**values)


def _state_from_record(record: MkSyncStateRecord) -> MkSyncState:
    values = {name: getattr(record, name) for name in MkSyncState.__dataclass_fields__}
    values["status"] = MkSyncStatus(record.status)
    return MkSyncState(**values)


def _run_to_record(item: MkSyncRun) -> MkSyncRunRecord:
    values = {name: getattr(item, name) for name in item.__dataclass_fields__}
    values["status"] = item.status.value
    return MkSyncRunRecord(**values)


def _run_from_record(record: MkSyncRunRecord) -> MkSyncRun:
    values = {name: getattr(record, name) for name in MkSyncRun.__dataclass_fields__}
    values["status"] = MkSyncStatus(record.status)
    return MkSyncRun(**values)


def _validate_limit(limit: int) -> None:
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
