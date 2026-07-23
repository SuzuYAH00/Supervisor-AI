from dataclasses import replace
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import ProcessingRunCursorPosition
from supervisor_ai.infrastructure.persistence.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyLedgerRepository,
    SqlAlchemyProcessingRunRepository,
)
from supervisor_ai.rules_engine import LedgerEntryType
from tests.persistence.factories import commercial_event, ledger_entry, processing_run


def seed(session: Session) -> SqlAlchemyProcessingRunRepository:
    events = SqlAlchemyEventRepository(session)
    runs = SqlAlchemyProcessingRunRepository(session)
    for index in range(1, 5):
        events.add(
            replace(
                commercial_event(
                    f"event-{index}",
                    external_reference=f"external-{index}",
                ),
                source="source-b" if index == 4 else "source-a",
            )
        )
    definitions = (
        ("run-1", "event-1", datetime(2026, 6, 30, 12, tzinfo=UTC), "posted", "v1"),
        ("run-2", "event-2", datetime(2026, 7, 10, 12, tzinfo=UTC), "failed", "v1"),
        ("run-3a", "event-3", datetime(2026, 7, 20, 12, tzinfo=UTC), "posted", "v1"),
        ("run-3b", "event-3", datetime(2026, 7, 20, 12, tzinfo=UTC), "posted", "v2"),
        ("run-4", "event-4", datetime(2026, 8, 1, 12, tzinfo=UTC), "failed", "v2"),
        ("run-5", "event-1", datetime(2026, 8, 2, 12, tzinfo=UTC), "posted", "v2"),
    )
    for run_id, event_id, started_at, status, version in definitions:
        runs.add(
            replace(
                processing_run(run_id, event_id),
                started_at=started_at,
                completed_at=started_at,
                final_status=status,
                rules_engine_version=version,
            )
        )
    ledger = SqlAlchemyLedgerRepository(session)
    ledger.add(ledger_entry("ledger-3", "event-3"))
    ledger.add(
        replace(
            ledger_entry("adjustment-3", "event-3"),
            entry_type=LedgerEntryType.ADJUSTMENT,
        )
    )
    session.commit()
    return runs


def search(repository: SqlAlchemyProcessingRunRepository, **changes: object):
    arguments = {
        "source": None,
        "external_reference": None,
        "final_status": None,
        "rules_engine_version": None,
        "start_date": None,
        "end_date": None,
        "after": None,
        "limit": 50,
    }
    arguments.update(changes)
    return repository.search(**arguments)


def test_empty_database(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        assert search(SqlAlchemyProcessingRunRepository(session)) == ()


def test_ordering_tie_break_and_ledger_do_not_multiply_runs(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        repository = seed(session)
        result = search(repository)
    assert [item.processing_run_id for item in result] == [
        "run-5",
        "run-4",
        "run-3b",
        "run-3a",
        "run-2",
        "run-1",
    ]
    assert result[2].event_id == result[3].event_id == "event-3"
    assert all(not hasattr(item, "phase_results") for item in result)


def test_all_exact_filters_and_inclusive_dates(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        repository = seed(session)
        assert [
            item.processing_run_id
            for item in search(repository, source="source-b")
        ] == ["run-4"]
        assert [
            item.processing_run_id
            for item in search(repository, external_reference="external-3")
        ] == ["run-3b", "run-3a"]
        assert [
            item.processing_run_id
            for item in search(repository, final_status="failed")
        ] == ["run-4", "run-2"]
        assert [
            item.processing_run_id
            for item in search(repository, rules_engine_version="v1")
        ] == ["run-3a", "run-2", "run-1"]
        assert [
            item.processing_run_id
            for item in search(
                repository,
                start_date=date(2026, 7, 10),
                end_date=date(2026, 7, 20),
            )
        ] == ["run-3b", "run-3a", "run-2"]
        assert [
            item.processing_run_id
            for item in search(
                repository,
                source="source-a",
                final_status="posted",
                rules_engine_version="v2",
            )
        ] == ["run-5", "run-3b"]


def test_keyset_pages_have_no_duplicates_or_omissions(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        repository = seed(session)
        first = search(repository, limit=2)
        second = search(
            repository,
            after=ProcessingRunCursorPosition(
                first[-1].started_at,
                first[-1].processing_run_id,
            ),
            limit=2,
        )
        third = search(
            repository,
            after=ProcessingRunCursorPosition(
                second[-1].started_at,
                second[-1].processing_run_id,
            ),
            limit=2,
        )
    identifiers = [
        item.processing_run_id for page in (first, second, third) for item in page
    ]
    assert identifiers == ["run-5", "run-4", "run-3b", "run-3a", "run-2", "run-1"]
    assert len(identifiers) == len(set(identifiers))
