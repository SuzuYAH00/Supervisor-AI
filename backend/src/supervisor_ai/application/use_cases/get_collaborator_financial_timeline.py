from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from supervisor_ai.application.persistence import (
    CollaboratorFinancialTimelineCursorPosition,
    CollaboratorFinancialTimelineRecord,
)
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.rules_engine import Currency, LedgerEntryType

DEFAULT_TIMELINE_LIMIT = 50
MAX_TIMELINE_LIMIT = 100
MAX_COLLABORATOR_ID_LENGTH = 128


@dataclass(frozen=True, slots=True)
class GetCollaboratorFinancialTimelineQuery:
    collaborator_id: str
    start_date: date | None = None
    end_date: date | None = None
    entry_type: LedgerEntryType | None = None
    currency: Currency | None = None
    limit: int = DEFAULT_TIMELINE_LIMIT
    after: CollaboratorFinancialTimelineCursorPosition | None = None

    def __post_init__(self) -> None:
        if not self.collaborator_id.strip():
            raise ValueError("collaborator_id must not be blank")
        if len(self.collaborator_id) > MAX_COLLABORATOR_ID_LENGTH:
            raise ValueError(
                "collaborator_id must not exceed "
                f"{MAX_COLLABORATOR_ID_LENGTH} characters"
            )
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")
        if not 1 <= self.limit <= MAX_TIMELINE_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_TIMELINE_LIMIT}")


@dataclass(frozen=True, slots=True)
class TimelineCommercialEvent:
    event_id: str
    external_reference: str
    source: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CollaboratorFinancialTimelineItem:
    ledger_entry_id: str
    posted_at: datetime
    entry_type: LedgerEntryType
    amount: Decimal
    currency: Currency
    invoice_id: str | None
    posting_reference: str
    remuneration_calculation_reference: str
    source_reference_ids: tuple[str, ...]
    commercial_event: TimelineCommercialEvent


@dataclass(frozen=True, slots=True)
class GetCollaboratorFinancialTimelineResult:
    filters: GetCollaboratorFinancialTimelineQuery
    items: tuple[CollaboratorFinancialTimelineItem, ...]
    has_more: bool
    next_cursor_position: CollaboratorFinancialTimelineCursorPosition | None


class GetCollaboratorFinancialTimelineUseCase:
    """Projeta lançamentos e eventos relacionados sem recalcular finanças."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, query: GetCollaboratorFinancialTimelineQuery
    ) -> GetCollaboratorFinancialTimelineResult:
        with self._unit_of_work_factory() as unit_of_work:
            records = unit_of_work.ledger.search_collaborator_timeline(
                collaborator_id=query.collaborator_id,
                start_date=query.start_date,
                end_date=query.end_date,
                entry_type=query.entry_type,
                currency=query.currency,
                after=query.after,
                limit=query.limit + 1,
            )
        has_more = len(records) > query.limit
        page = records[: query.limit]
        return GetCollaboratorFinancialTimelineResult(
            filters=query,
            items=tuple(_timeline_item(record) for record in page),
            has_more=has_more,
            next_cursor_position=(
                CollaboratorFinancialTimelineCursorPosition(
                    page[-1].posted_at,
                    page[-1].ledger_entry_id,
                )
                if has_more
                else None
            ),
        )


def _timeline_item(
    record: CollaboratorFinancialTimelineRecord,
) -> CollaboratorFinancialTimelineItem:
    return CollaboratorFinancialTimelineItem(
        ledger_entry_id=record.ledger_entry_id,
        posted_at=record.posted_at,
        entry_type=record.entry_type,
        amount=record.amount,
        currency=record.currency,
        invoice_id=record.invoice_id,
        posting_reference=record.posting_reference,
        remuneration_calculation_reference=(
            record.remuneration_calculation_reference
        ),
        source_reference_ids=record.source_reference_ids,
        commercial_event=TimelineCommercialEvent(
            event_id=record.event_id,
            external_reference=record.external_reference,
            source=record.event_source,
            occurred_at=record.event_occurred_at,
        ),
    )
