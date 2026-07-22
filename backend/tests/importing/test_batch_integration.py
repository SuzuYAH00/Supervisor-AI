from copy import deepcopy
from pathlib import Path

from sqlalchemy import Engine

from supervisor_ai.bootstrap import (
    build_batch_processor,
    build_session_factory,
    build_unit_of_work_factory,
)
from supervisor_ai.database.base import Base
from supervisor_ai.infrastructure.importing import BatchDocument
from tests.importing.factories import complete_document, json_text


def batch_document(index: int) -> BatchDocument[str]:
    value = deepcopy(complete_document())
    event = value["event"]
    evaluation = value["evaluation"]
    snapshot = value["financial_snapshot"]
    assert isinstance(event, dict)
    assert isinstance(evaluation, dict)
    assert isinstance(snapshot, dict)
    payment = snapshot["payment"]
    remuneration = snapshot["remuneration"]
    posting = snapshot["posting"]
    assert isinstance(payment, dict)
    assert isinstance(remuneration, dict)
    assert isinstance(posting, dict)

    event_id = f"event-batch-{index}"
    event["id"] = event_id
    event["external_reference"] = f"external-batch-{index}"
    event["raw_payload"] = {"contract_id": f"contract-batch-{index}"}
    evaluation["evaluation_id"] = f"00000000-0000-0000-0000-{index:012d}"
    evaluation["subject_id"] = f"contract-batch-{index}"
    payment["invoice_id"] = f"invoice-batch-{index}"
    remuneration["payment_validation_reference"] = f"payment:{event_id}"
    posting["posting_reference"] = f"posting:{event_id}"
    posting["remuneration_calculation_reference"] = f"calculation:{event_id}"
    return BatchDocument(f"source-document-{index}", json_text(value))


def test_real_batch_is_atomic_per_document_and_idempotent(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'batch.sqlite3'}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)
    processor = build_batch_processor(database_url)
    documents = tuple(batch_document(index) for index in range(1, 4))

    first = processor.process(documents)
    second = processor.process(documents)

    assert first.statistics.total_documents == 3
    assert first.statistics.successful_documents == 3
    assert first.statistics.processing_runs_created == 3
    assert first.statistics.ledger_entries_created == 3
    assert second.statistics.successful_documents == 3
    assert second.statistics.processing_runs_created == 3
    assert second.statistics.ledger_entries_created == 0
    assert tuple(item.document_identifier for item in first.ordered_results) == (
        "source-document-1",
        "source-document-2",
        "source-document-3",
    )

    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        for index in range(1, 4):
            event_id = f"event-batch-{index}"
            assert unit_of_work.events.get_by_id(event_id) is not None
            assert len(unit_of_work.processing_runs.find_by_event_id(event_id)) == 2
            assert unit_of_work.ledger.find_credit_by_event_id(event_id) is not None

    engine.dispose()


def test_invalid_middle_document_does_not_rollback_other_documents(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'partial-batch.sqlite3'}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)
    processor = build_batch_processor(database_url)
    documents = (
        batch_document(1),
        BatchDocument("invalid-document", "{not-json"),
        batch_document(3),
    )

    batch = processor.process(documents)

    assert tuple(item.processing_status for item in batch.ordered_results) == (
        "success",
        "validation_error",
        "success",
    )
    assert batch.statistics.total_documents == 3
    assert batch.statistics.successful_documents == 2
    assert batch.statistics.validation_errors == 1
    assert batch.statistics.processing_runs_created == 2
    assert batch.statistics.ledger_entries_created == 2

    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        for index in (1, 3):
            event_id = f"event-batch-{index}"
            assert unit_of_work.events.get_by_id(event_id) is not None
            assert len(unit_of_work.processing_runs.find_by_event_id(event_id)) == 1
            assert unit_of_work.ledger.find_credit_by_event_id(event_id) is not None

    engine.dispose()
