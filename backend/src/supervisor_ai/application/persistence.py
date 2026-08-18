from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from supervisor_ai.rules_engine import (
    ClassificationIdentity,
    CsatCompetitiveChannel,
    Currency,
    LedgerEntryType,
)

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
class CsatEvaluation:
    id: str
    external_reference: str
    source: str
    collaborator_id: str
    channel: str | None
    score: Decimal
    evaluated_at: datetime
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        required = {
            "id": self.id,
            "external_reference": self.external_reference,
            "source": self.source,
            "collaborator_id": self.collaborator_id,
        }
        for name, value in required.items():
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
        limits = {
            "id": (self.id, 128),
            "external_reference": (self.external_reference, 255),
            "source": (self.source, 100),
            "collaborator_id": (self.collaborator_id, 128),
        }
        for name, (value, maximum) in limits.items():
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")
        if self.channel is not None and not self.channel.strip():
            raise ValueError("channel must not be blank when provided")
        if self.channel is not None and len(self.channel) > 100:
            raise ValueError("channel must not exceed 100 characters")
        if not self.score.is_finite():
            raise ValueError("score must be finite")
        _, digits, exponent = self.score.as_tuple()
        decimal_places = max(-exponent, 0)
        integer_places = max(len(digits) + exponent, 0)
        if decimal_places > 6 or integer_places > 14:
            raise ValueError("score exceeds persisted numeric precision")
        _require_aware(self.evaluated_at, "evaluated_at")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class CsatContact:
    id: str
    external_reference: str
    source: str
    collaborator_id: str
    external_operator_identity: str
    occurred_on: date
    source_channel: CsatCompetitiveChannel
    score: Decimal | None
    source_context: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        values = {
            "id": (self.id, 128),
            "external_reference": (self.external_reference, 255),
            "source": (self.source, 100),
            "collaborator_id": (self.collaborator_id, 128),
            "external_operator_identity": (self.external_operator_identity, 255),
        }
        for name, (value, maximum) in values.items():
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")
        if not isinstance(self.source_channel, CsatCompetitiveChannel):
            raise ValueError("source_channel must be chat or phone")
        if self.source_context is not None:
            if not self.source_context.strip():
                raise ValueError("source_context must not be blank when provided")
            if len(self.source_context) > 255:
                raise ValueError("source_context must not exceed 255 characters")
        if self.score is not None:
            if not self.score.is_finite():
                raise ValueError("score must be finite")
            _, digits, exponent = self.score.as_tuple()
            decimal_places = max(-exponent, 0)
            integer_places = max(len(digits) + exponent, 0)
            if decimal_places > 6 or integer_places > 14:
                raise ValueError("score exceeds persisted numeric precision")
            minimum = (
                Decimal("0")
                if self.source_channel is CsatCompetitiveChannel.CHAT
                else Decimal("1")
            )
            if self.score < minimum or self.score > Decimal("5"):
                raise ValueError("score is outside the source scale")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class OperationalCollaboratorProfile:
    collaborator_id: str
    competitive_channel: CsatCompetitiveChannel
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.collaborator_id.strip():
            raise ValueError("collaborator_id must not be blank")
        if len(self.collaborator_id) > 128:
            raise ValueError("collaborator_id must not exceed 128 characters")
        if not isinstance(self.competitive_channel, CsatCompetitiveChannel):
            raise ValueError("competitive_channel must be chat or phone")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class CollaboratorExternalIdentity:
    collaborator_id: str
    source: str
    external_identity: str
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        values = {
            "collaborator_id": (self.collaborator_id, 128),
            "source": (self.source, 100),
            "external_identity": (self.external_identity, 255),
        }
        for name, (value, maximum) in values.items():
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class AttendanceFact:
    id: str
    external_reference: str
    source: str
    customer_code: str
    operator_id: str
    channel: str
    occurred_at: datetime
    process: ClassificationIdentity
    opening_classification: ClassificationIdentity
    closing_classification: ClassificationIdentity
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        required = {
            "id": self.id,
            "external_reference": self.external_reference,
            "source": self.source,
            "customer_code": self.customer_code,
            "operator_id": self.operator_id,
            "channel": self.channel,
        }
        for name, value in required.items():
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
        limits = {
            "id": (self.id, 128),
            "external_reference": (self.external_reference, 255),
            "source": (self.source, 100),
            "customer_code": (self.customer_code, 128),
            "operator_id": (self.operator_id, 128),
            "channel": (self.channel, 100),
        }
        for name, (value, maximum) in limits.items():
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")
        for identity, name in (
            (self.process, "process"),
            (self.opening_classification, "opening classification"),
            (self.closing_classification, "closing classification"),
        ):
            if identity.code is not None and len(identity.code) > 20:
                raise ValueError(f"{name} code must not exceed 20 characters")
            if len(identity.description) > 255:
                raise ValueError(
                    f"{name} description must not exceed 255 characters"
                )
        _require_aware(self.occurred_at, "occurred_at")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class DailyWorkStatusFact:
    id: str
    collaborator_id: str
    work_date: date
    competence_month: date
    raw_code: str
    source: str
    external_reference: str
    source_sheet: str
    source_cell: str
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        values = {
            "id": (self.id, 128),
            "collaborator_id": (self.collaborator_id, 128),
            "raw_code": (self.raw_code, 20),
            "source": (self.source, 100),
            "external_reference": (self.external_reference, 255),
            "source_sheet": (self.source_sheet, 100),
            "source_cell": (self.source_cell, 20),
        }
        for name, (value, maximum) in values.items():
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")
        if self.raw_code != self.raw_code.strip():
            raise ValueError("raw_code must be trimmed")
        if self.competence_month.day != 1:
            raise ValueError("competence_month must be the first day of a month")
        if (
            self.work_date.year,
            self.work_date.month,
        ) != (self.competence_month.year, self.competence_month.month):
            raise ValueError("work_date must belong to competence_month")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class CsatSummaryGroupRecord:
    value: str | None
    evaluation_count: int
    score_total: Decimal


@dataclass(frozen=True, slots=True)
class CsatSummaryRecord:
    evaluation_count: int
    score_total: Decimal
    by_collaborator: tuple[CsatSummaryGroupRecord, ...]
    by_channel: tuple[CsatSummaryGroupRecord, ...]


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
class CollaboratorFinancialTimelineCursorPosition:
    posted_at: datetime
    ledger_entry_id: str

    def __post_init__(self) -> None:
        _require_aware(self.posted_at, "posted_at")
        if not self.ledger_entry_id.strip():
            raise ValueError("ledger_entry_id must not be blank")
        if len(self.ledger_entry_id) > 255:
            raise ValueError("ledger_entry_id must not exceed 255 characters")


@dataclass(frozen=True, slots=True)
class CollaboratorFinancialTimelineRecord:
    ledger_entry_id: str
    posted_at: datetime
    entry_type: LedgerEntryType
    amount: Decimal
    currency: Currency
    invoice_id: str | None
    posting_reference: str
    remuneration_calculation_reference: str
    source_reference_ids: tuple[str, ...]
    event_id: str
    external_reference: str
    event_source: str
    event_occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ProcessingHealthCount:
    value: str
    count: int


@dataclass(frozen=True, slots=True)
class ProcessingHealthRecord:
    processing_run_total: int
    by_final_status: tuple[ProcessingHealthCount, ...]
    by_rules_engine_version: tuple[ProcessingHealthCount, ...]
    events_with_processing_runs: int
    events_without_processing_runs: int
    events_with_multiple_processing_runs: int
    events_with_ledger_entries: int
    events_without_ledger_entries: int


@dataclass(frozen=True, slots=True)
class ProcessingRunCursorPosition:
    started_at: datetime
    processing_run_id: str

    def __post_init__(self) -> None:
        _require_aware(self.started_at, "started_at")
        if not self.processing_run_id.strip():
            raise ValueError("processing_run_id must not be blank")
        if len(self.processing_run_id) > 128:
            raise ValueError("processing_run_id must not exceed 128 characters")


@dataclass(frozen=True, slots=True)
class ProcessingRunListRecord:
    processing_run_id: str
    event_id: str
    source: str
    external_reference: str
    started_at: datetime
    completed_at: datetime
    final_status: str
    rules_engine_version: str


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
