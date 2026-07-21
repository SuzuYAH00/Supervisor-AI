import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.infrastructure.persistence.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyProcessingRunRepository,
)
from tests.persistence.factories import commercial_event, processing_run


def test_event_accepts_multiple_runs_and_preserves_metadata(
    session_factory: sessionmaker[Session],
) -> None:
    first = processing_run("run-1")
    second = processing_run("run-2")
    second.phase_results.append({"phase": "ledger", "status": "posted"})
    with session_factory() as session:
        SqlAlchemyEventRepository(session).add(commercial_event())
        repository = SqlAlchemyProcessingRunRepository(session)
        repository.add(first)
        repository.add(second)
        session.commit()
        session.expunge_all()

        assert repository.get_by_id(first.id) == first
        assert repository.find_by_event_id("event-1") == (first, second)


def test_run_rejects_unknown_event(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        with pytest.raises(IntegrityError):
            SqlAlchemyProcessingRunRepository(session).add(
                processing_run("run-1", "missing-event")
            )
