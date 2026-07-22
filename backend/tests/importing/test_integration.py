from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select

from supervisor_ai.application import LedgerConflict
from supervisor_ai.bootstrap import (
    build_json_importer,
    build_session_factory,
    build_unit_of_work_factory,
)
from supervisor_ai.database.base import Base
from supervisor_ai.infrastructure.persistence.models import CommercialEventRecord
from tests.importing.factories import complete_document, json_text


def test_json_importer_persists_and_reprocesses_idempotently(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'json-import.sqlite3'}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)
    importer = build_json_importer(database_url)

    first = importer.import_document(json_text())
    second = importer.import_document(json_text())

    assert first.final_status == second.final_status == "not_evaluable"
    assert first.event_persisted is True
    assert second.event_persisted is False
    assert first.processing_run_id != second.processing_run_id
    assert first.ledger_entry_id is second.ledger_entry_id is None
    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        event = unit_of_work.events.get_by_id("event-json-1")
        assert event is not None
        assert event.raw_payload["contract_id"] == "contract-1"
        runs = unit_of_work.processing_runs.find_by_event_id("event-json-1")
        assert len(runs) == 2
        assert all(len(run.phase_results) == 7 for run in runs)
        assert unit_of_work.ledger.find_credit_by_event_id("event-json-1") is None

    with session_factory() as session:
        count = session.scalar(
            select(func.count()).select_from(CommercialEventRecord)
        )
        assert count == 1
    engine.dispose()


def test_complete_json_flow_persists_credit_and_reprocesses_idempotently(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'financial-import.sqlite3'}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)
    importer = build_json_importer(database_url)

    first = importer.import_document(json_text(complete_document()))
    second = importer.import_document(json_text(complete_document()))

    assert first.final_status == "posted"
    assert first.ledger_persisted is True
    assert first.ledger_already_existed is False
    assert second.event_persisted is False
    assert second.ledger_persisted is False
    assert second.ledger_already_existed is True
    assert first.processing_run_id != second.processing_run_id

    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        assert unit_of_work.events.get_by_id("event-json-1") is not None
        runs = unit_of_work.processing_runs.find_by_event_id("event-json-1")
        assert len(runs) == 2
        entry = unit_of_work.ledger.find_credit_by_event_id("event-json-1")
        assert entry is not None
        assert entry.amount == Decimal("99.90")
        assert entry.beneficiary_id == "employee-1"
        assert entry.source_reference_ids == ("invoice-1", "ticket-1")
        assert entry.remuneration_calculation_reference == (
            "calculation:event-json-1"
        )
    engine.dispose()


def test_changed_economic_fact_never_creates_second_credit(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'ledger-conflict.sqlite3'}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)
    importer = build_json_importer(database_url)
    importer.import_document(json_text(complete_document()))
    changed = complete_document()
    snapshot = changed["financial_snapshot"]
    assert isinstance(snapshot, dict)
    remuneration = snapshot["remuneration"]
    assert isinstance(remuneration, dict)
    remuneration["full_new_plan_amount"] = "109.90"

    with pytest.raises(LedgerConflict):
        importer.import_document(json_text(changed))

    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        assert len(unit_of_work.processing_runs.find_by_event_id("event-json-1")) == 1
        entry = unit_of_work.ledger.find_credit_by_event_id("event-json-1")
        assert entry is not None
        assert entry.amount == Decimal("99.90")
    engine.dispose()
