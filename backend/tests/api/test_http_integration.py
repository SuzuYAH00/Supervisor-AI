import asyncio
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import Engine

from supervisor_ai.bootstrap import (
    build_http_application,
    build_session_factory,
    build_unit_of_work_factory,
)
from supervisor_ai.database.base import Base
from tests.importing.csv_factories import csv_row, csv_text


def prepared_application(tmp_path: Path, name: str) -> tuple[FastAPI, str, Engine]:
    database_url = f"sqlite+pysqlite:///{tmp_path / name}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)
    return build_http_application(database_url), database_url, engine


def request(
    application: FastAPI,
    method: str,
    path: str,
    *,
    content: str | None = None,
) -> Response:
    async def execute() -> Response:
        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            files = (
                None
                if content is None
                else {"file": ("commercial.csv", content.encode(), "text/csv")}
            )
            return await client.request(method, path, files=files)

    return asyncio.run(execute())


def post_csv(application: FastAPI, content: str) -> Response:
    return request(application, "POST", "/imports/csv", content=content)


def test_http_batch_preserves_partial_failures_and_transactions(
    tmp_path: Path,
) -> None:
    application, database_url, engine = prepared_application(
        tmp_path, "http-partial.sqlite3"
    )
    rows = [csv_row(index) for index in range(1, 6)]
    rows[1]["invoice_recurring_amount"] = "99,90"
    rows[3]["external_reference"] = rows[0]["external_reference"]

    response = post_csv(application, csv_text(rows))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial_failure"
    assert body["parsing"]["converted_rows"] == 4
    assert body["parsing"]["error_rows"] == 1
    assert body["processing"]["successful_documents"] == 3
    assert body["processing"]["business_conflicts"] == 1
    assert body["processing"]["ledger_entries_created"] == 3

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


def test_http_reimport_is_idempotent(tmp_path: Path) -> None:
    application, database_url, engine = prepared_application(
        tmp_path, "http-idempotent.sqlite3"
    )
    content = csv_text([csv_row(1), csv_row(2)])
    first = post_csv(application, content)
    second = post_csv(application, content)
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "success"
    assert first.json()["processing"]["ledger_entries_created"] == 2
    assert second.json()["processing"]["ledger_entries_created"] == 0

    session_factory = build_session_factory(database_url)
    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        for index in (1, 2):
            event_id = f"event-csv-{index}"
            assert len(unit_of_work.processing_runs.find_by_event_id(event_id)) == 2
            assert unit_of_work.ledger.find_credit_by_event_id(event_id) is not None
    engine.dispose()


def test_composition_root_does_not_create_database_or_import_on_startup(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "not-created.sqlite3"
    application = build_http_application(f"sqlite+pysqlite:///{database_path}")
    assert application.title == "Supervisor AI"
    assert not database_path.exists()
    response = request(application, "GET", "/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert not database_path.exists()
