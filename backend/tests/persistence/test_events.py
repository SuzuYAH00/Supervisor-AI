from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import CommercialEvent
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
