from dataclasses import replace
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.infrastructure.persistence.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyLedgerRepository,
    SqlAlchemyProcessingHealthRepository,
    SqlAlchemyProcessingRunRepository,
)
from supervisor_ai.rules_engine import LedgerEntryType
from tests.persistence.factories import commercial_event, ledger_entry, processing_run


def seed(session: Session) -> None:
    events = SqlAlchemyEventRepository(session)
    runs = SqlAlchemyProcessingRunRepository(session)
    ledger = SqlAlchemyLedgerRepository(session)
    moments = {
        "event-1": datetime(2026, 6, 30, 10, tzinfo=UTC),
        "event-2": datetime(2026, 7, 1, 10, tzinfo=UTC),
        "event-3": datetime(2026, 7, 15, 10, tzinfo=UTC),
        "event-4": datetime(2026, 7, 31, 10, tzinfo=UTC),
        "event-5": datetime(2026, 8, 1, 10, tzinfo=UTC),
    }
    for number, (event_id, occurred_at) in enumerate(moments.items(), 1):
        source = "other-source" if event_id == "event-4" else "csv-example"
        events.add(
            replace(
                commercial_event(
                    event_id,
                    external_reference=f"external-{number}",
                ),
                source=source,
                occurred_at=occurred_at,
                received_at=occurred_at,
            )
        )

    runs.add(
        replace(
            processing_run("run-2", "event-2"),
            final_status="posted",
            started_at=datetime(2026, 7, 1, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 1, 0, 1, tzinfo=UTC),
            rules_engine_version="rules-1",
        )
    )
    runs.add(
        replace(
            processing_run("run-3a", "event-3"),
            final_status="not_evaluable",
            started_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
            completed_at=datetime(2026, 7, 15, 12, 1, tzinfo=UTC),
            rules_engine_version="rules-1",
        )
    )
    runs.add(
        replace(
            processing_run("run-3b", "event-3"),
            final_status="posted",
            started_at=datetime(2026, 7, 31, 23, 59, tzinfo=UTC),
            completed_at=datetime(2026, 7, 31, 23, 59, 1, tzinfo=UTC),
            rules_engine_version="rules-2",
        )
    )
    runs.add(
        replace(
            processing_run("run-4", "event-4"),
            final_status="not_evaluable",
            started_at=datetime(2026, 7, 20, 12, tzinfo=UTC),
            completed_at=datetime(2026, 7, 20, 12, 1, tzinfo=UTC),
            rules_engine_version="rules-2",
        )
    )
    runs.add(
        replace(
            processing_run("run-5", "event-5"),
            final_status="posted",
            started_at=datetime(2026, 8, 1, 0, tzinfo=UTC),
            completed_at=datetime(2026, 8, 1, 0, 1, tzinfo=UTC),
            rules_engine_version="rules-1",
        )
    )

    ledger.add(replace(ledger_entry("ledger-2", "event-2"), invoice_id="invoice-2"))
    ledger.add(replace(ledger_entry("ledger-3", "event-3"), invoice_id="invoice-3"))
    ledger.add(
        replace(
            ledger_entry("adjustment-3", "event-3"),
            entry_type=LedgerEntryType.ADJUSTMENT,
            posting_reference="adjustment-3",
        )
    )
    session.commit()


def query(
    session_factory: sessionmaker[Session],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    source: str | None = None,
    rules_engine_version: str | None = None,
):
    with session_factory() as session:
        return SqlAlchemyProcessingHealthRepository(session).get_processing_health(
            start_date=start_date,
            end_date=end_date,
            source=source,
            rules_engine_version=rules_engine_version,
        )


def counts(items) -> dict[str, int]:
    return {item.value: item.count for item in items}


def test_empty_database(session_factory: sessionmaker[Session]) -> None:
    result = query(session_factory)
    assert result.processing_run_total == 0
    assert result.by_final_status == result.by_rules_engine_version == ()
    assert result.events_with_processing_runs == 0
    assert result.events_without_processing_runs == 0
    assert result.events_with_ledger_entries == 0


def test_aggregates_without_join_multiplication(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed(session)
    result = query(session_factory)
    assert result.processing_run_total == 5
    assert counts(result.by_final_status) == {"not_evaluable": 2, "posted": 3}
    assert counts(result.by_rules_engine_version) == {"rules-1": 3, "rules-2": 2}
    assert result.events_with_processing_runs == 4
    assert result.events_without_processing_runs == 1
    assert result.events_with_multiple_processing_runs == 1
    assert result.events_with_ledger_entries == 2
    assert result.events_without_ledger_entries == 3
    assert [item.value for item in result.by_final_status] == [
        "not_evaluable",
        "posted",
    ]


def test_source_filter_applies_to_runs_and_full_event_cohort(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed(session)
    result = query(session_factory, source="csv-example")
    assert result.processing_run_total == 4
    assert result.events_with_processing_runs == 3
    assert result.events_without_processing_runs == 1
    assert result.events_with_multiple_processing_runs == 1
    assert result.events_with_ledger_entries == 2
    assert result.events_without_ledger_entries == 2


def test_processing_window_is_inclusive_and_scopes_event_cohort(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed(session)
    result = query(
        session_factory,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )
    assert result.processing_run_total == 4
    assert result.events_with_processing_runs == 3
    assert result.events_without_processing_runs == 0
    assert result.events_with_multiple_processing_runs == 1
    assert result.events_with_ledger_entries == 2
    assert result.events_without_ledger_entries == 1


def test_version_and_combined_filters_scope_all_metrics(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed(session)
    result = query(
        session_factory,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        source="csv-example",
        rules_engine_version="rules-2",
    )
    assert result.processing_run_total == 1
    assert counts(result.by_final_status) == {"posted": 1}
    assert counts(result.by_rules_engine_version) == {"rules-2": 1}
    assert result.events_with_processing_runs == 1
    assert result.events_without_processing_runs == 0
    assert result.events_with_multiple_processing_runs == 0
    assert result.events_with_ledger_entries == 1
    assert result.events_without_ledger_entries == 0


def test_period_without_runs_is_empty(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        seed(session)
    result = query(
        session_factory,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )
    assert result.processing_run_total == 0
    assert result.events_with_processing_runs == 0
    assert result.events_without_processing_runs == 0
    assert result.events_with_ledger_entries == 0
