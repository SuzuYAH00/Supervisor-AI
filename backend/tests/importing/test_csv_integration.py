from pathlib import Path

from sqlalchemy import Engine

from supervisor_ai.bootstrap import (
    build_csv_import_service,
    build_session_factory,
    build_unit_of_work_factory,
)
from supervisor_ai.database.base import Base
from tests.importing.csv_factories import csv_row, csv_text


def database(tmp_path: Path, name: str) -> tuple[str, Engine]:
    database_url = f"sqlite+pysqlite:///{tmp_path / name}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)
    return database_url, engine


def test_csv_service_preserves_partial_failures_and_line_order(
    tmp_path: Path,
) -> None:
    database_url, engine = database(tmp_path, "csv-partial.sqlite3")
    rows = [csv_row(index) for index in range(1, 6)]
    rows[1]["invoice_recurring_amount"] = "99,90"
    rows[3]["external_reference"] = rows[0]["external_reference"]
    service = build_csv_import_service(database_url)

    result = service.import_csv(csv_text(rows))

    assert result.parsing.statistics.total_data_rows == 5
    assert result.parsing.statistics.converted_rows == 4
    assert result.parsing.statistics.error_rows == 1
    assert result.parsing.rows[1].line_number == 3
    assert result.parsing.rows[1].errors[0].column == "invoice_recurring_amount"
    assert tuple(
        item.document_identifier for item in result.batch.ordered_results
    ) == ("csv-row-1", "csv-row-3", "csv-row-4", "csv-row-5")
    assert tuple(item.processing_status for item in result.batch.ordered_results) == (
        "success",
        "success",
        "business_conflict",
        "success",
    )
    assert result.batch.statistics.successful_documents == 3
    assert result.batch.statistics.business_conflicts == 1
    assert result.batch.statistics.ledger_entries_created == 3

    session_factory = build_session_factory(database_url)
    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        for index in (1, 3, 5):
            event_id = f"event-csv-{index}"
            assert unit_of_work.events.get_by_id(event_id) is not None
            assert len(unit_of_work.processing_runs.find_by_event_id(event_id)) == 1
            assert unit_of_work.ledger.find_credit_by_event_id(event_id) is not None
        assert unit_of_work.events.get_by_id("event-csv-2") is None
        assert unit_of_work.events.get_by_id("event-csv-4") is None

    engine.dispose()


def test_reimporting_same_csv_is_idempotent(tmp_path: Path) -> None:
    database_url, engine = database(tmp_path, "csv-idempotent.sqlite3")
    service = build_csv_import_service(database_url)
    content = csv_text([csv_row(1), csv_row(2), csv_row(3)])

    first = service.import_csv(content)
    second = service.import_csv(content)

    assert first.batch.statistics.ledger_entries_created == 3
    assert second.batch.statistics.ledger_entries_created == 0
    assert tuple(item.document_identifier for item in first.batch.ordered_results) == (
        "csv-row-1",
        "csv-row-2",
        "csv-row-3",
    )
    assert tuple(item.document_identifier for item in second.batch.ordered_results) == (
        "csv-row-1",
        "csv-row-2",
        "csv-row-3",
    )
    assert all(not item.event_persisted for item in second.batch.ordered_results)
    assert all(item.ledger_already_existed for item in second.batch.ordered_results)

    session_factory = build_session_factory(database_url)
    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        for index in range(1, 4):
            event_id = f"event-csv-{index}"
            assert len(unit_of_work.processing_runs.find_by_event_id(event_id)) == 2
            assert unit_of_work.ledger.find_credit_by_event_id(event_id) is not None

    engine.dispose()
