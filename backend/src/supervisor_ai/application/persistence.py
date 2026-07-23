from dataclasses import dataclass, field
from datetime import UTC, datetime

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CommercialEvent:
    id: str
    external_reference: str
    source: str
    occurred_at: datetime
    received_at: datetime
    raw_payload: dict[str, JsonValue]
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.id or not self.external_reference or not self.source:
            raise ValueError("event identifiers and source are required")
        _require_aware(self.occurred_at, "occurred_at")
        _require_aware(self.received_at, "received_at")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class CommercialEventCursorPosition:
    occurred_at: datetime
    event_id: str

    def __post_init__(self) -> None:
        _require_aware(self.occurred_at, "occurred_at")
        if not self.event_id.strip():
            raise ValueError("event_id must not be blank")
        if len(self.event_id) > 128:
            raise ValueError("event_id must not exceed 128 characters")


@dataclass(frozen=True, slots=True)
class ProcessingRun:
    id: str
    event_id: str
    final_status: str
    started_at: datetime
    completed_at: datetime
    rules_engine_version: str
    phase_results: list[JsonValue]
    warnings: list[JsonValue]
    audit_references: list[JsonValue]
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.id or not self.event_id or not self.final_status:
            raise ValueError("processing run identifiers and status are required")
        if not self.rules_engine_version:
            raise ValueError("rules_engine_version is required")
        for name in ("started_at", "completed_at", "created_at"):
            _require_aware(getattr(self, name), name)
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
