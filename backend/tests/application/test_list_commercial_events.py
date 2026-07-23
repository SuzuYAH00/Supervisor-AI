from dataclasses import fields, replace
from datetime import UTC, date, datetime, timedelta
from types import TracebackType

import pytest

from supervisor_ai.application import (
    CommercialEvent,
    CommercialEventCursorPosition,
)
from supervisor_ai.application.use_cases import (
    ListCommercialEventsQuery,
    ListCommercialEventsUseCase,
)
from tests.persistence.factories import commercial_event

NOW = datetime(2026, 7, 22, 12, tzinfo=UTC)


class EventRepositoryFake:
    def __init__(
        self,
        events: tuple[CommercialEvent, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.events = events
        self.error = error
        self.arguments: dict[str, object] = {}

    def search(self, **arguments: object) -> tuple[CommercialEvent, ...]:
        self.arguments = arguments
        if self.error is not None:
            raise self.error
        return self.events


class UnitOfWorkFake:
    def __init__(self, events: EventRepositoryFake) -> None:
        self.events = events
        self.closed = False
        self.rolled_back = False
        self.commits = 0

    def __enter__(self) -> "UnitOfWorkFake":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        self.closed = True
        self.rolled_back = exc_type is not None

    def commit(self) -> None:
        self.commits += 1


def event(event_id: str, occurred_at: datetime) -> CommercialEvent:
    return replace(
        commercial_event(event_id, external_reference=f"external-{event_id}"),
        occurred_at=occurred_at,
    )


def execute(
    events: tuple[CommercialEvent, ...] = (),
    query: ListCommercialEventsQuery | None = None,
    error: Exception | None = None,
):
    repository = EventRepositoryFake(events, error)
    unit_of_work = UnitOfWorkFake(repository)
    result = ListCommercialEventsUseCase(lambda: unit_of_work).execute(
        query or ListCommercialEventsQuery()
    )
    return result, repository, unit_of_work


def test_empty_result_uses_defaults_and_is_read_only() -> None:
    result, repository, unit_of_work = execute()
    assert result.items == ()
    assert result.has_more is False
    assert result.next_cursor_position is None
    assert repository.arguments == {
        "source": None,
        "external_reference": None,
        "start_date": None,
        "end_date": None,
        "after": None,
        "limit": 51,
    }
    assert unit_of_work.closed and not unit_of_work.rolled_back
    assert unit_of_work.commits == 0


def test_filters_cursor_and_limit_plus_one_are_forwarded() -> None:
    position = CommercialEventCursorPosition(NOW, "event-2")
    query = ListCommercialEventsQuery(
        source="csv",
        external_reference="external-2",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        limit=2,
        after=position,
    )
    _, repository, _ = execute(query=query)
    assert repository.arguments == {
        "source": "csv",
        "external_reference": "external-2",
        "start_date": date(2026, 7, 1),
        "end_date": date(2026, 7, 31),
        "after": position,
        "limit": 3,
    }


def test_has_more_trims_extra_item_and_uses_last_returned_position() -> None:
    events = (
        event("event-3", NOW + timedelta(hours=1)),
        event("event-2", NOW),
        event("event-1", NOW - timedelta(hours=1)),
    )
    original = tuple(item.id for item in events)
    result, _, _ = execute(events, ListCommercialEventsQuery(limit=2))
    assert tuple(item.event_id for item in result.items) == ("event-3", "event-2")
    assert result.has_more is True
    assert result.next_cursor_position == CommercialEventCursorPosition(
        NOW, "event-2"
    )
    assert tuple(item.id for item in events) == original
    assert "raw_payload" not in {field.name for field in fields(result.items[0])}


def test_last_page_has_no_cursor_and_preserves_repository_order() -> None:
    events = (event("event-2", NOW), event("event-1", NOW))
    result, _, _ = execute(events, ListCommercialEventsQuery(limit=2))
    assert tuple(item.event_id for item in result.items) == ("event-2", "event-1")
    assert not result.has_more
    assert result.next_cursor_position is None


@pytest.mark.parametrize(
    "query",
    [
        ListCommercialEventsQuery,
    ],
)
def test_query_type_is_immutable(query) -> None:
    instance = query()
    with pytest.raises(AttributeError):
        instance.limit = 10


@pytest.mark.parametrize(
    "arguments",
    [
        {"source": ""},
        {"source": "   "},
        {"source": "x" * 101},
        {"external_reference": ""},
        {"external_reference": "x" * 256},
        {"limit": 0},
        {"limit": 101},
        {"start_date": date(2026, 8, 1), "end_date": date(2026, 7, 31)},
    ],
)
def test_query_rejects_invalid_filters(arguments: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ListCommercialEventsQuery(**arguments)


@pytest.mark.parametrize("limit", [1, 50, 100])
def test_query_accepts_limit_boundaries(limit: int) -> None:
    assert ListCommercialEventsQuery(limit=limit).limit == limit


def test_repository_failure_rolls_back_context_without_commit() -> None:
    repository = EventRepositoryFake(error=RuntimeError("database failed"))
    unit_of_work = UnitOfWorkFake(repository)
    service = ListCommercialEventsUseCase(lambda: unit_of_work)
    with pytest.raises(RuntimeError, match="database failed"):
        service.execute(ListCommercialEventsQuery())
    assert unit_of_work.closed and unit_of_work.rolled_back
    assert unit_of_work.commits == 0
