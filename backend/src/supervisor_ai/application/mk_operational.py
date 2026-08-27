from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

MK_EXTERNAL_IDENTITY_SOURCE = "mk"
MK_SOURCE = MK_EXTERNAL_IDENTITY_SOURCE
MK_ATTENDANCE_FACT_SOURCE = "mk_postgresql"
MK_ATTENDANCE_PLAN_CHANGE_LINK_POLICY = "temporal_link_rejected"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_aware(value: datetime | None, field_name: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field_name} must be timezone-aware")


def _require_identity(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if len(value) > 255:
        raise ValueError(f"{field_name} must not exceed 255 characters")


class MkUpsertOutcome(StrEnum):
    INSERTED = "inserted"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


class MkSyncStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class MkOperatorResolutionStatus(StrEnum):
    EXACT_EXTERNAL_ID = "exact_external_id"
    MANUAL_MAPPING_REQUIRED = "manual_mapping_required"


def mk_user_external_identity(user_id: int) -> str:
    if user_id <= 0:
        raise ValueError("MK user_id must be positive")
    return str(user_id)


@dataclass(frozen=True, slots=True)
class MkAttendanceMirror:
    external_id: str
    protocol: str | None
    customer_external_id: str | None
    opened_at: datetime
    closed_at: datetime | None
    opening_operator_external_id: str | None
    closing_operator_external_id: str | None
    process_external_id: str | None
    subprocess_external_id: str | None
    opening_classification_external_id: str | None
    closing_classification_external_id: str | None
    origin_external_id: str | None
    status: str | None
    is_finalized: bool | None
    mk_dialog_session_external_id: str | None
    source_first_seen_at: datetime
    source_last_seen_at: datetime
    local_created_at: datetime = field(default_factory=_utc_now)
    local_updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _require_identity(self.external_id, "external_id")
        for name in (
            "opened_at",
            "closed_at",
            "source_first_seen_at",
            "source_last_seen_at",
            "local_created_at",
            "local_updated_at",
        ):
            _require_aware(getattr(self, name), name)
        if self.source_last_seen_at < self.source_first_seen_at:
            raise ValueError("source_last_seen_at cannot precede source_first_seen_at")


@dataclass(frozen=True, slots=True)
class MkBotConversationMirror:
    external_id: str
    protocol: str | None
    person_external_id: str | None
    integration_external_reference: str | None
    conversation_type: str | None
    sector_external_id: str | None
    created_at: datetime
    human_service_started_at: datetime | None
    queue_entered_at: datetime | None
    closed_at: datetime | None
    score: int | None
    final_operator_external_id: str | None
    source_first_seen_at: datetime
    source_last_seen_at: datetime
    local_created_at: datetime = field(default_factory=_utc_now)
    local_updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _require_identity(self.external_id, "external_id")
        for name in (
            "created_at",
            "human_service_started_at",
            "queue_entered_at",
            "closed_at",
            "source_first_seen_at",
            "source_last_seen_at",
            "local_created_at",
            "local_updated_at",
        ):
            _require_aware(getattr(self, name), name)
        if self.source_last_seen_at < self.source_first_seen_at:
            raise ValueError("source_last_seen_at cannot precede source_first_seen_at")


@dataclass(frozen=True, slots=True)
class MkContractMirror:
    external_id: str
    customer_external_id: str
    current_plan_external_id: str
    cancelled: str | None
    suspended: str | None
    joined_on: date | None
    activated_at: datetime | None
    source_first_seen_at: datetime
    source_last_seen_at: datetime
    local_created_at: datetime = field(default_factory=_utc_now)
    local_updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        for name in ("external_id", "customer_external_id", "current_plan_external_id"):
            _require_identity(getattr(self, name), name)
        _validate_mirror_times(self)


@dataclass(frozen=True, slots=True)
class MkPlanMirror:
    external_id: str
    description: str
    monthly_value: Decimal | None
    download_speed: int | None
    upload_speed: int | None
    formatted_speeds: str | None
    source_first_seen_at: datetime
    source_last_seen_at: datetime
    local_created_at: datetime = field(default_factory=_utc_now)
    local_updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _require_identity(self.external_id, "external_id")
        if not self.description.strip():
            raise ValueError("description must not be blank")
        _validate_mirror_times(self)


@dataclass(frozen=True, slots=True)
class MkContractPlanChangeMirror:
    external_id: str
    contract_external_id: str
    operation_code: int
    old_plan_external_id: str | None
    new_plan_external_id: str | None
    changed_at: datetime
    changed_by_login: str
    changed_by_operator_external_id: str | None
    value_delta: Decimal | None
    extra_context: str | None
    source_first_seen_at: datetime
    source_last_seen_at: datetime
    local_created_at: datetime = field(default_factory=_utc_now)
    local_updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        for name in ("external_id", "contract_external_id", "changed_by_login"):
            _require_identity(getattr(self, name), name)
        if self.operation_code <= 0:
            raise ValueError("operation_code must be positive")
        if (
            self.old_plan_external_id is not None
            and self.old_plan_external_id == self.new_plan_external_id
        ):
            raise ValueError("old and new plan identities must differ")
        _validate_mirror_times(self, "changed_at")


def _validate_mirror_times(item: Any, *additional: str) -> None:
    names = (
        *additional,
        "source_first_seen_at",
        "source_last_seen_at",
        "local_created_at",
        "local_updated_at",
    )
    for name in names:
        _require_aware(getattr(item, name), name)
    if item.source_last_seen_at < item.source_first_seen_at:
        raise ValueError("source_last_seen_at cannot precede source_first_seen_at")


@dataclass(frozen=True, slots=True)
class MkSyncState:
    source: str
    entity_type: str
    last_pk: int | None
    last_success_at: datetime | None
    last_attempt_at: datetime | None
    status: MkSyncStatus
    last_error: str | None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _require_identity(self.source, "source")
        _require_identity(self.entity_type, "entity_type")
        if self.last_pk is not None and self.last_pk < 0:
            raise ValueError("last_pk must not be negative")
        for name in ("last_success_at", "last_attempt_at", "created_at", "updated_at"):
            _require_aware(getattr(self, name), name)
        if self.last_error is not None and len(self.last_error) > 1000:
            raise ValueError("last_error must not exceed 1000 characters")


@dataclass(frozen=True, slots=True)
class MkSyncRun:
    id: str
    source: str
    entity_type: str
    initial_cursor: int | None
    final_cursor: int | None
    inserted: int
    updated: int
    unchanged: int
    rejected: int
    status: MkSyncStatus
    started_at: datetime
    finished_at: datetime | None
    error: str | None
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        for name, value in (
            ("id", self.id),
            ("source", self.source),
            ("entity_type", self.entity_type),
        ):
            _require_identity(value, name)
        for name in ("inserted", "updated", "unchanged", "rejected"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must not be negative")
        for name in ("started_at", "finished_at", "created_at"):
            _require_aware(getattr(self, name), name)
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        if self.error is not None and len(self.error) > 1000:
            raise ValueError("error must not exceed 1000 characters")
