from dataclasses import dataclass
from datetime import date, datetime

from supervisor_ai.application.persistence import (
    CommercialEvent,
    CommercialEventCursorPosition,
)
from supervisor_ai.application.ports import UnitOfWorkFactory

DEFAULT_COMMERCIAL_EVENTS_LIMIT = 50
MAX_COMMERCIAL_EVENTS_LIMIT = 100
MAX_SOURCE_LENGTH = 100
MAX_EXTERNAL_REFERENCE_LENGTH = 255


@dataclass(frozen=True, slots=True)
class ListCommercialEventsQuery:
    source: str | None = None
    external_reference: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int = DEFAULT_COMMERCIAL_EVENTS_LIMIT
    after: CommercialEventCursorPosition | None = None

    def __post_init__(self) -> None:
        _validate_optional_text(self.source, "source", MAX_SOURCE_LENGTH)
        _validate_optional_text(
            self.external_reference,
            "external_reference",
            MAX_EXTERNAL_REFERENCE_LENGTH,
        )
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")
        if not 1 <= self.limit <= MAX_COMMERCIAL_EVENTS_LIMIT:
            raise ValueError(
                f"limit must be between 1 and {MAX_COMMERCIAL_EVENTS_LIMIT}"
            )


@dataclass(frozen=True, slots=True)
class CommercialEventListItem:
    event_id: str
    external_reference: str
    source: str
    occurred_at: datetime
    received_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ListCommercialEventsResult:
    filters: ListCommercialEventsQuery
    items: tuple[CommercialEventListItem, ...]
    has_more: bool
    next_cursor_position: CommercialEventCursorPosition | None


class ListCommercialEventsUseCase:
    """Lista eventos persistidos por keyset, sem executar regras."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: ListCommercialEventsQuery) -> ListCommercialEventsResult:
        with self._unit_of_work_factory() as unit_of_work:
            events = unit_of_work.events.search(
                source=query.source,
                external_reference=query.external_reference,
                start_date=query.start_date,
                end_date=query.end_date,
                after=query.after,
                limit=query.limit + 1,
            )
        has_more = len(events) > query.limit
        page = events[: query.limit]
        items = tuple(_list_item(event) for event in page)
        next_position = (
            CommercialEventCursorPosition(
                occurred_at=page[-1].occurred_at,
                event_id=page[-1].id,
            )
            if has_more
            else None
        )
        return ListCommercialEventsResult(
            filters=query,
            items=items,
            has_more=has_more,
            next_cursor_position=next_position,
        )


def _validate_optional_text(
    value: str | None,
    field_name: str,
    maximum_length: int,
) -> None:
    if value is None:
        return
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if len(value) > maximum_length:
        raise ValueError(f"{field_name} must not exceed {maximum_length} characters")


def _list_item(event: CommercialEvent) -> CommercialEventListItem:
    return CommercialEventListItem(
        event_id=event.id,
        external_reference=event.external_reference,
        source=event.source,
        occurred_at=event.occurred_at,
        received_at=event.received_at,
        created_at=event.created_at,
    )
