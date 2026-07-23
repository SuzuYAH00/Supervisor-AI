from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import CommercialEvent, CommercialEventCursorPosition
from supervisor_ai.infrastructure.persistence.repositories import (
    SqlAlchemyEventRepository,
)
from tests.persistence.factories import commercial_event


def test_saves_and_recovers_event_with_payload(
    session_factory: sessionmaker[Session],
) -> None:
    expected = commercial_event()
    with session_factory() as session:
        repository = SqlAlchemyEventRepository(session)
        repository.add(expected)
        session.commit()
        session.expunge_all()

        assert repository.get_by_id(expected.id) == expected
        assert repository.get_by_external_reference(
            expected.external_reference
        ) == expected


def test_missing_event_returns_none(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        repository = SqlAlchemyEventRepository(session)
        assert repository.get_by_id("missing") is None
        assert repository.get_by_external_reference("missing") is None


def test_event_requires_aware_dates() -> None:
    with pytest.raises(ValueError, match="occurred_at"):
        CommercialEvent(
            id="event-1",
            external_reference="external-1",
            source="source",
            occurred_at=datetime(2026, 7, 20),
            received_at=datetime(2026, 7, 20, tzinfo=UTC),
            raw_payload={},
        )


def test_database_rejects_empty_required_source(
    session_factory: sessionmaker[Session],
) -> None:
    event = commercial_event()
    object.__setattr__(event, "source", "")
    with session_factory() as session:
        with pytest.raises(IntegrityError):
            SqlAlchemyEventRepository(session).add(event)


def test_database_rejects_duplicate_external_reference(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        repository = SqlAlchemyEventRepository(session)
        repository.add(commercial_event("event-1"))
        with pytest.raises(IntegrityError):
            repository.add(commercial_event("event-2"))


def test_search_applies_filters_keyset_order_and_database_limit(
    session_factory: sessionmaker[Session],
) -> None:
    same_time = datetime(2026, 7, 20, 12, tzinfo=UTC)
    events = (
        replace(
            commercial_event("event-5", external_reference="external-5"),
            source="api",
            occurred_at=datetime(2026, 8, 1, 12, tzinfo=UTC),
        ),
        replace(
            commercial_event("event-4", external_reference="external-4"),
            source="csv",
            occurred_at=same_time,
        ),
        replace(
            commercial_event("event-3", external_reference="external-3"),
            source="csv",
            occurred_at=same_time,
        ),
        replace(
            commercial_event("event-2", external_reference="external-2"),
            source="csv",
            occurred_at=datetime(2026, 7, 1, 0, tzinfo=UTC),
        ),
        replace(
            commercial_event("event-1", external_reference="external-1"),
            source="legacy",
            occurred_at=datetime(2026, 6, 30, 23, 59, tzinfo=UTC),
        ),
    )
    with session_factory() as session:
        repository = SqlAlchemyEventRepository(session)
        for item in events:
            repository.add(item)
        session.commit()

        first_page = repository.search(
            source=None,
            external_reference=None,
            start_date=None,
            end_date=None,
            after=None,
            limit=2,
        )
        second_page = repository.search(
            source=None,
            external_reference=None,
            start_date=None,
            end_date=None,
            after=CommercialEventCursorPosition(
                first_page[-1].occurred_at, first_page[-1].id
            ),
            limit=3,
        )
        csv_in_july = repository.search(
            source="csv",
            external_reference=None,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 20),
            after=None,
            limit=10,
        )
        exact = repository.search(
            source="csv",
            external_reference="external-3",
            start_date=None,
            end_date=None,
            after=None,
            limit=10,
        )
        missing_cursor_event = repository.search(
            source=None,
            external_reference=None,
            start_date=None,
            end_date=None,
            after=CommercialEventCursorPosition(same_time, "event-9"),
            limit=10,
        )

    assert tuple(item.id for item in first_page) == ("event-5", "event-4")
    assert tuple(item.id for item in second_page) == (
        "event-3",
        "event-2",
        "event-1",
    )
    assert tuple(item.id for item in csv_in_july) == (
        "event-4",
        "event-3",
        "event-2",
    )
    assert tuple(item.id for item in exact) == ("event-3",)
    assert tuple(item.id for item in missing_cursor_event) == (
        "event-4",
        "event-3",
        "event-2",
        "event-1",
    )
