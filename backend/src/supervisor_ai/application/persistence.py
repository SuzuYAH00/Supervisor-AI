from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
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
                raise ValueError(f"{name} description must not exceed 255 characters")
        _require_aware(self.occurred_at, "occurred_at")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class IngestionCoverageEvidence:
    dataset: str
    source: str
    import_reference: str
    covered_through: date
    recorded_at: datetime

    def __post_init__(self) -> None:
        for name, value, maximum in (
            ("dataset", self.dataset, 100),
            ("source", self.source, 100),
            ("import_reference", self.import_reference, 255),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")
        _require_aware(self.recorded_at, "recorded_at")


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
class CollaboratorWorkSchedule:
    id: str
    collaborator_id: str
    standard_start: time
    standard_end: time
    effective_from: date
    effective_until: date | None
    source: str
    source_reference: str
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _validate_schedule_identity(self)
        _validate_schedule_times(self.standard_start, self.standard_end)
        if (
            self.effective_until is not None
            and self.effective_until < self.effective_from
        ):
            raise ValueError("effective_until must not precede effective_from")


@dataclass(frozen=True, slots=True)
class DailyPlannedWorkScheduleFact:
    id: str
    collaborator_id: str
    work_date: date
    planned_start: time | None
    planned_end: time | None
    source_type: str
    source: str
    source_reference: str
    source_sheet: str
    source_cell: str
    unresolved_reason: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _validate_schedule_identity(self)
        for name in ("source_type", "source_sheet", "source_cell"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        resolved = self.planned_start is not None and self.planned_end is not None
        if resolved:
            _validate_schedule_times(self.planned_start, self.planned_end)
            if self.unresolved_reason is not None:
                raise ValueError("resolved schedule must not have unresolved_reason")
        elif self.planned_start is not None or self.planned_end is not None:
            raise ValueError("planned_start and planned_end must be provided together")
        elif not self.unresolved_reason or not self.unresolved_reason.strip():
            raise ValueError("unresolved schedule requires unresolved_reason")

    @property
    def is_resolved(self) -> bool:
        return self.planned_start is not None


@dataclass(frozen=True, slots=True)
class DailyWorkScheduleOverride:
    id: str
    collaborator_id: str
    work_date: date
    planned_start: time
    planned_end: time
    reason: str
    created_by: str
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        for name in ("id", "collaborator_id", "reason", "created_by"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        _validate_schedule_times(self.planned_start, self.planned_end)


def _validate_schedule_identity(item: object) -> None:
    for name in ("id", "collaborator_id", "source", "source_reference"):
        value = getattr(item, name)
        if not value.strip():
            raise ValueError(f"{name} must not be blank")


def _validate_schedule_times(start: time, end: time) -> None:
    if start.tzinfo is not None or end.tzinfo is not None:
        raise ValueError("schedule times must be civil times without timezone")
    if end <= start:
        raise ValueError("schedule end must be after start")


@dataclass(frozen=True, slots=True)
class EmployeeOccurrenceReport:
    id: str
    external_reference: str
    source: str
    collaborator_id: str
    external_collaborator_identity: str
    submitted_at: datetime
    occurrence_date: date
    reason_text: str
    source_sheet: str
    source_row: int
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        values = {
            "id": (self.id, 128),
            "external_reference": (self.external_reference, 255),
            "source": (self.source, 100),
            "collaborator_id": (self.collaborator_id, 128),
            "external_collaborator_identity": (
                self.external_collaborator_identity,
                255,
            ),
            "source_sheet": (self.source_sheet, 100),
        }
        for name, (value, maximum) in values.items():
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")
        if not self.reason_text.strip():
            raise ValueError("reason_text must not be blank")
        if self.source_row < 2:
            raise ValueError("source_row must identify a data row")
        _require_aware(self.submitted_at, "submitted_at")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class WorkSessionFact:
    id: str
    external_reference: str
    source: str
    collaborator_id: str
    external_collaborator_identity: str
    external_agent_id: str | None
    queue: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: int
    source_extract_reference: str
    source_sheet: str
    source_row: int
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _validate_npx_fact(self)


@dataclass(frozen=True, slots=True)
class PauseFact:
    id: str
    external_reference: str
    source: str
    collaborator_id: str
    external_collaborator_identity: str
    external_agent_id: str | None
    queue: str
    pause_type: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: int
    supervisor_released: str | None
    source_extract_reference: str
    source_sheet: str
    source_row: int
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _validate_npx_fact(self)
        if not self.pause_type.strip():
            raise ValueError("pause_type must not be blank")


@dataclass(frozen=True, slots=True)
class DelayOccurrence:
    id: str
    collaborator_id: str
    occurrence_date: date
    occurrence_type: str
    source_fact_type: str
    source_fact_id: str
    observed_seconds: int
    applied_limit_seconds: int
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        for name in (
            "id",
            "collaborator_id",
            "occurrence_type",
            "source_fact_type",
            "source_fact_id",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        if self.observed_seconds < 0 or self.applied_limit_seconds < 0:
            raise ValueError("delay seconds must not be negative")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class DelayReview:
    id: str
    delay_occurrence_id: str
    decision: str
    decided_at: datetime
    decided_by: str
    employee_occurrence_report_id: str | None = None
    note: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        for name in ("id", "delay_occurrence_id", "decision", "decided_by"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        if self.decision not in {"valid", "corrected"}:
            raise ValueError("decision must be valid or corrected")
        _require_aware(self.decided_at, "decided_at")
        _require_aware(self.created_at, "created_at")


def _validate_npx_fact(fact: WorkSessionFact | PauseFact) -> None:
    for name in (
        "id",
        "external_reference",
        "source",
        "collaborator_id",
        "external_collaborator_identity",
        "queue",
        "source_extract_reference",
        "source_sheet",
    ):
        if not getattr(fact, name).strip():
            raise ValueError(f"{name} must not be blank")
    if fact.source_row < 2:
        raise ValueError("source_row must identify a data row")
    if fact.duration_seconds < 0:
        raise ValueError("duration_seconds must not be negative")
    _require_aware(fact.started_at, "started_at")
    _require_aware(fact.ended_at, "ended_at")
    _require_aware(fact.created_at, "created_at")
    if fact.ended_at < fact.started_at:
        raise ValueError("ended_at cannot precede started_at")


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
