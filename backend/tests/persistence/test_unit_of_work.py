import pytest
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from tests.persistence.factories import commercial_event


def test_commit_persists(session_factory: sessionmaker[Session]) -> None:
    event = commercial_event()
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.events.add(event)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.events.get_by_id("event-1") == event


def test_exit_without_commit_does_not_persist(
    session_factory: sessionmaker[Session],
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.events.add(commercial_event())

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.events.get_by_id("event-1") is None


def test_exception_rolls_back(session_factory: sessionmaker[Session]) -> None:
    with pytest.raises(RuntimeError, match="stop"):
        with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
            unit_of_work.events.add(commercial_event())
            raise RuntimeError("stop")

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.events.get_by_id("event-1") is None


def test_repositories_share_session_and_session_is_released(
    session_factory: sessionmaker[Session],
) -> None:
    unit_of_work = SqlAlchemyUnitOfWork(session_factory)
    with unit_of_work:
        assert unit_of_work.events.session is unit_of_work.ledger.session
        assert unit_of_work.events.session is unit_of_work.processing_runs.session

    assert unit_of_work._session is None
