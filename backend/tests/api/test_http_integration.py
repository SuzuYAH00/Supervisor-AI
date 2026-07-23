import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
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
from supervisor_ai.rules_engine import Currency, LedgerEntryType
from tests.importing.csv_factories import csv_row, csv_text
from tests.persistence.factories import commercial_event, ledger_entry, processing_run


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


def test_imported_credits_are_queryable_with_filters_and_remain_idempotent(
    tmp_path: Path,
) -> None:
    application, database_url, engine = prepared_application(
        tmp_path, "http-financial-snapshot.sqlite3"
    )
    rows = [csv_row(index) for index in range(1, 4)]
    rows[0]["beneficiary_id"] = "collaborator-1"
    rows[0]["posted_at"] = "2026-07-05T12:00:00Z"
    rows[1]["beneficiary_id"] = "collaborator-2"
    rows[1]["posted_at"] = "2026-07-20T12:00:00Z"
    rows[2]["beneficiary_id"] = "collaborator-1"
    rows[2]["posted_at"] = "2026-08-05T12:00:00Z"
    content = csv_text(rows)

    first_import = post_csv(application, content)
    complete = request(application, "GET", "/financial/snapshot")
    collaborator = request(
        application,
        "GET",
        "/financial/snapshot?collaborator_id=collaborator-1",
    )
    july = request(
        application,
        "GET",
        "/financial/snapshot?start_date=2026-07-01&end_date=2026-07-31",
    )
    combined = request(
        application,
        "GET",
        (
            "/financial/snapshot?collaborator_id=collaborator-1"
            "&start_date=2026-07-01&end_date=2026-07-31"
        ),
    )
    second_import = post_csv(application, content)
    after_reimport = request(application, "GET", "/financial/snapshot")

    assert first_import.status_code == second_import.status_code == 200
    assert complete.status_code == collaborator.status_code == july.status_code == 200
    assert combined.status_code == after_reimport.status_code == 200
    assert complete.json()["credit_count"] == 3
    assert complete.json()["totals_by_currency"] == [
        {"currency": "BRL", "amount": "299.70"}
    ]
    assert tuple(item["ledger_entry_id"] for item in complete.json()["items"]) == (
        "ledger.remuneration.credit:event-csv-1",
        "ledger.remuneration.credit:event-csv-2",
        "ledger.remuneration.credit:event-csv-3",
    )
    assert collaborator.json()["credit_count"] == 2
    assert july.json()["credit_count"] == 2
    assert combined.json()["credit_count"] == 1
    assert after_reimport.json()["credit_count"] == 3
    assert second_import.json()["processing"]["ledger_entries_created"] == 0

    session_factory = build_session_factory(database_url)
    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        for index in range(1, 4):
            event_id = f"event-csv-{index}"
            assert len(unit_of_work.processing_runs.find_by_event_id(event_id)) == 2
    engine.dispose()


def test_financial_summary_aggregates_ranks_filters_and_remains_idempotent(
    tmp_path: Path,
) -> None:
    application, _, engine = prepared_application(
        tmp_path, "http-financial-summary.sqlite3"
    )
    rows = [csv_row(index) for index in range(1, 5)]
    collaborators = ("alice", "alice", "bob", "charlie")
    amounts = ("120.00", "120.00", "150.00", "50.00")
    dates = ("2026-07-05", "2026-07-20", "2026-07-25", "2026-08-05")
    for row, collaborator, amount, posted_date in zip(
        rows, collaborators, amounts, dates, strict=True
    ):
        row["beneficiary_id"] = collaborator
        row["posted_at"] = f"{posted_date}T12:05:00Z"
        row["invoice_recurring_amount"] = amount
        row["expected_recurring_amount"] = amount
        row["previous_recurring_value"] = "10.00"
        row["current_recurring_value"] = amount
        row["previous_remuneration_recurring_amount"] = "10.00"
        row["new_remuneration_recurring_amount"] = amount
        row["full_new_plan_amount"] = amount
    content = csv_text(rows)

    first = post_csv(application, content)
    complete = request(application, "GET", "/financial/summary")
    july = request(
        application,
        "GET",
        "/financial/summary?start_date=2026-07-01&end_date=2026-07-31",
    )
    alice = request(
        application,
        "GET",
        "/financial/summary?collaborator_id=alice",
    )
    second = post_csv(application, content)
    after_reimport = request(application, "GET", "/financial/summary")

    assert first.status_code == second.status_code == complete.status_code == 200
    body = complete.json()
    assert body["collaborator_count"] == 3
    assert body["credit_count"] == 4
    assert body["totals_by_currency"] == [
        {"currency": "BRL", "amount": "440.00"}
    ]
    brl = {
        item["collaborator_id"]: item["totals_by_currency"][0]
        for item in body["collaborators"]
    }
    assert brl["alice"] == {
        "currency": "BRL",
        "amount": "240.00",
        "credit_count": 2,
        "rank": 1,
        "share_percentage": "54.55",
    }
    assert brl["bob"]["rank"] == 2
    assert brl["bob"]["share_percentage"] == "34.09"
    assert brl["charlie"]["rank"] == 3
    assert brl["charlie"]["share_percentage"] == "11.36"
    assert july.json()["credit_count"] == 3
    assert july.json()["collaborator_count"] == 2
    assert alice.json()["credit_count"] == 2
    assert alice.json()["totals_by_currency"] == [
        {"currency": "BRL", "amount": "240.00"}
    ]
    assert alice.json()["collaborators"][0]["totals_by_currency"][0][
        "share_percentage"
    ] == "100.00"
    assert second.json()["processing"]["ledger_entries_created"] == 0
    assert after_reimport.json() == body
    engine.dispose()


def test_financial_summary_keeps_currencies_independent(tmp_path: Path) -> None:
    application, database_url, engine = prepared_application(
        tmp_path, "http-financial-summary-currencies.sqlite3"
    )
    unit_of_work_factory = build_unit_of_work_factory(
        build_session_factory(database_url)
    )
    with unit_of_work_factory() as unit_of_work:
        unit_of_work.events.add(commercial_event("event-brl", external_reference="brl"))
        unit_of_work.events.add(commercial_event("event-usd", external_reference="usd"))
        unit_of_work.ledger.add(
            replace(
                ledger_entry("ledger-brl", "event-brl", amount=Decimal("100.00")),
                beneficiary_id="alice",
            )
        )
        unit_of_work.ledger.add(
            replace(
                ledger_entry("ledger-usd", "event-usd", amount=Decimal("40.00")),
                beneficiary_id="bob",
                currency=Currency.USD,
            )
        )
        unit_of_work.commit()

    response = request(application, "GET", "/financial/summary")
    assert response.status_code == 200
    assert response.json()["totals_by_currency"] == [
        {"currency": "BRL", "amount": "100.00"},
        {"currency": "USD", "amount": "40.00"},
    ]
    collaborators = {
        item["collaborator_id"]: item for item in response.json()["collaborators"]
    }
    assert collaborators["alice"]["totals_by_currency"][0]["rank"] == 1
    assert collaborators["bob"]["totals_by_currency"][0]["rank"] == 1
    assert all(
        item["totals_by_currency"][0]["share_percentage"] == "100.00"
        for item in collaborators.values()
    )
    engine.dispose()


def test_commercial_event_drill_down_preserves_ledger_and_records_reprocessing(
    tmp_path: Path,
) -> None:
    application, _, engine = prepared_application(
        tmp_path, "http-commercial-event-details.sqlite3"
    )
    content = csv_text([csv_row(1)])

    first_import = post_csv(application, content)
    snapshot = request(application, "GET", "/financial/snapshot")
    event_id = snapshot.json()["items"][0]["commercial_event_id"]
    first_details = request(
        application, "GET", f"/commercial-events/{event_id}"
    )
    second_import = post_csv(application, content)
    second_details = request(
        application, "GET", f"/commercial-events/{event_id}"
    )
    missing = request(
        application, "GET", "/commercial-events/event-does-not-exist"
    )

    assert first_import.status_code == snapshot.status_code == 200
    assert first_details.status_code == second_import.status_code == 200
    assert second_details.status_code == 200
    first_body = first_details.json()
    second_body = second_details.json()
    assert first_body["commercial_event"]["event_id"] == "event-csv-1"
    assert first_body["commercial_event"]["external_reference"] == "external-csv-1"
    assert len(first_body["ledger_entries"]) == 1
    assert first_body["ledger_entries"][0]["ledger_entry_id"] == (
        "ledger.remuneration.credit:event-csv-1"
    )
    assert first_body["ledger_entries"][0]["amount"] == "99.90"
    assert len(first_body["processing_runs"]) == 1
    assert len(second_body["ledger_entries"]) == 1
    assert len(second_body["processing_runs"]) == 2
    assert second_import.json()["processing"]["ledger_entries_created"] == 0
    assert tuple(
        (run["started_at"], run["processing_run_id"])
        for run in second_body["processing_runs"]
    ) == tuple(
        sorted(
            (run["started_at"], run["processing_run_id"])
            for run in second_body["processing_runs"]
        )
    )
    assert "raw_payload" not in first_details.text
    assert "raw_payload" not in second_details.text
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "commercial_event_not_found"
    engine.dispose()


def test_commercial_event_list_uses_keyset_filters_and_includes_unposted_events(
    tmp_path: Path,
) -> None:
    application, database_url, engine = prepared_application(
        tmp_path, "http-commercial-event-list.sqlite3"
    )
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
            occurred_at=datetime(2026, 7, 1, 12, tzinfo=UTC),
        ),
        replace(
            commercial_event("event-1", external_reference="external-1"),
            source="legacy",
            occurred_at=datetime(2026, 6, 1, 12, tzinfo=UTC),
        ),
    )
    unit_of_work_factory = build_unit_of_work_factory(
        build_session_factory(database_url)
    )
    with unit_of_work_factory() as unit_of_work:
        for event in events:
            unit_of_work.events.add(event)
        unit_of_work.commit()

    pages = []
    cursor: str | None = None
    for _ in range(3):
        suffix = "" if cursor is None else f"&cursor={cursor}"
        response = request(
            application, "GET", f"/commercial-events?limit=2{suffix}"
        )
        assert response.status_code == 200
        body = response.json()
        pages.extend(item["event_id"] for item in body["items"])
        cursor = body["page"]["next_cursor"]

    csv_only = request(
        application, "GET", "/commercial-events?source=csv"
    )
    exact = request(
        application,
        "GET",
        "/commercial-events?external_reference=external-3",
    )
    july = request(
        application,
        "GET",
        "/commercial-events?start_date=2026-07-01&end_date=2026-07-31",
    )
    details = request(application, "GET", "/commercial-events/event-4")
    empty = request(
        application, "GET", "/commercial-events?source=does-not-exist"
    )
    invalid = request(
        application, "GET", "/commercial-events?cursor=invalid***"
    )

    assert pages == ["event-5", "event-4", "event-3", "event-2", "event-1"]
    assert len(pages) == len(set(pages)) == 5
    assert [item["event_id"] for item in csv_only.json()["items"]] == [
        "event-4",
        "event-3",
        "event-2",
    ]
    assert [item["event_id"] for item in exact.json()["items"]] == ["event-3"]
    assert [item["event_id"] for item in july.json()["items"]] == [
        "event-4",
        "event-3",
        "event-2",
    ]
    assert details.status_code == 200
    assert details.json()["ledger_entries"] == []
    assert details.json()["processing_runs"] == []
    assert "raw_payload" not in details.text
    assert empty.status_code == 200 and empty.json()["items"] == []
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_cursor"
    engine.dispose()


def test_collaborator_financial_timeline_pages_filters_and_drills_down(
    tmp_path: Path,
) -> None:
    application, database_url, engine = prepared_application(
        tmp_path, "http-collaborator-timeline.sqlite3"
    )
    same_time = datetime(2026, 7, 20, 13, tzinfo=UTC)
    events = tuple(
        commercial_event(f"event-{index}", external_reference=f"external-{index}")
        for index in range(1, 7)
    )
    entries = (
        replace(
            ledger_entry("ledger-6", "event-6", amount=Decimal("60.00")),
            beneficiary_id="bob",
            posted_at=datetime(2026, 8, 1, 13, tzinfo=UTC),
        ),
        replace(
            ledger_entry("ledger-5", "event-5", amount=Decimal("50.00")),
            beneficiary_id="alice",
            entry_type=LedgerEntryType.DEBIT,
            currency=Currency.USD,
            posted_at=datetime(2026, 7, 25, 13, tzinfo=UTC),
        ),
        replace(
            ledger_entry("ledger-4", "event-4", amount=Decimal("40.00")),
            beneficiary_id="alice",
            entry_type=LedgerEntryType.ADJUSTMENT,
            posted_at=same_time,
        ),
        replace(
            ledger_entry("ledger-3", "event-3", amount=Decimal("30.00")),
            beneficiary_id="alice",
            posted_at=same_time,
        ),
        replace(
            ledger_entry("ledger-2", "event-2", amount=Decimal("20.00")),
            beneficiary_id="alice",
            posted_at=datetime(2026, 7, 10, 13, tzinfo=UTC),
        ),
        replace(
            ledger_entry("ledger-1", "event-1", amount=Decimal("10.00")),
            beneficiary_id="alice",
            posted_at=datetime(2026, 6, 1, 13, tzinfo=UTC),
        ),
    )
    unit_of_work_factory = build_unit_of_work_factory(
        build_session_factory(database_url)
    )
    with unit_of_work_factory() as unit_of_work:
        for event in events:
            unit_of_work.events.add(event)
        for entry in entries:
            unit_of_work.ledger.add(entry)
        unit_of_work.commit()

    identifiers: list[str] = []
    cursor: str | None = None
    for _ in range(3):
        suffix = "" if cursor is None else f"&cursor={cursor}"
        response = request(
            application,
            "GET",
            f"/collaborators/alice/financial-timeline?limit=2{suffix}",
        )
        assert response.status_code == 200
        identifiers.extend(item["ledger_entry_id"] for item in response.json()["items"])
        cursor = response.json()["page"]["next_cursor"]

    debit = request(
        application,
        "GET",
        "/collaborators/alice/financial-timeline?entry_type=debit",
    )
    usd = request(
        application,
        "GET",
        "/collaborators/alice/financial-timeline?currency=USD",
    )
    july = request(
        application,
        "GET",
        (
            "/collaborators/alice/financial-timeline"
            "?start_date=2026-07-01&end_date=2026-07-31"
        ),
    )
    bob = request(
        application, "GET", "/collaborators/bob/financial-timeline"
    )
    empty = request(
        application, "GET", "/collaborators/unknown/financial-timeline"
    )
    invalid = request(
        application,
        "GET",
        "/collaborators/alice/financial-timeline?cursor=invalid***",
    )
    details = request(application, "GET", "/commercial-events/event-5")

    assert identifiers == [
        "ledger-5",
        "ledger-4",
        "ledger-3",
        "ledger-2",
        "ledger-1",
    ]
    assert len(identifiers) == len(set(identifiers)) == 5
    assert [item["ledger_entry_id"] for item in debit.json()["items"]] == [
        "ledger-5"
    ]
    assert [item["ledger_entry_id"] for item in usd.json()["items"]] == [
        "ledger-5"
    ]
    assert [item["ledger_entry_id"] for item in july.json()["items"]] == [
        "ledger-5",
        "ledger-4",
        "ledger-3",
        "ledger-2",
    ]
    assert [item["ledger_entry_id"] for item in bob.json()["items"]] == [
        "ledger-6"
    ]
    assert empty.status_code == 200 and empty.json()["items"] == []
    assert invalid.status_code == 422
    assert details.status_code == 200
    assert details.json()["ledger_entries"][0]["amount"] == (
        debit.json()["items"][0]["amount"]
    )
    assert "raw_payload" not in debit.text
    engine.dispose()


def test_processing_run_drill_down_is_allowlisted_and_read_only(
    tmp_path: Path,
) -> None:
    application, _, engine = prepared_application(
        tmp_path, "http-processing-run-details.sqlite3"
    )
    content = csv_text([csv_row(1)])
    first_import = post_csv(application, content)
    second_import = post_csv(application, content)
    event_details_before = request(
        application, "GET", "/commercial-events/event-csv-1"
    )
    run_ids = [
        run["processing_run_id"]
        for run in event_details_before.json()["processing_runs"]
    ]

    first_run = request(
        application, "GET", f"/processing-runs/{run_ids[0]}"
    )
    second_run = request(
        application, "GET", f"/processing-runs/{run_ids[1]}"
    )
    event_details_after = request(
        application, "GET", "/commercial-events/event-csv-1"
    )
    missing = request(
        application, "GET", "/processing-runs/run-does-not-exist"
    )
    invalid = request(application, "GET", "/processing-runs/%20%20")

    assert first_import.status_code == second_import.status_code == 200
    assert second_import.json()["processing"]["ledger_entries_created"] == 0
    assert len(run_ids) == 2
    assert first_run.status_code == second_run.status_code == 200
    assert first_run.json()["processing_run"]["event_id"] == "event-csv-1"
    assert second_run.json()["processing_run"]["event_id"] == "event-csv-1"
    assert first_run.json()["commercial_event"]["event_id"] == "event-csv-1"
    assert [phase["phase"] for phase in first_run.json()["phases"]] == [
        "contract_facts",
        "commercial_classification",
        "operational_context",
        "remuneration_eligibility",
        "payment_validation",
        "remuneration_amount",
        "ledger_posting",
    ]
    assert len(event_details_after.json()["processing_runs"]) == 2
    assert len(event_details_after.json()["ledger_entries"]) == 1
    assert event_details_after.json()["processing_runs"] == (
        event_details_before.json()["processing_runs"]
    )
    for response in (first_run, second_run):
        for absent in (
            "raw_payload",
            "warnings",
            "audit_references",
            "output",
            "Traceback",
            "SQLAlchemy",
        ):
            assert absent not in response.text
    assert missing.status_code == 404
    assert invalid.status_code == 422
    engine.dispose()


def test_processing_health_aggregates_persisted_data_without_side_effects(
    tmp_path: Path,
) -> None:
    application, database_url, engine = prepared_application(
        tmp_path, "http-processing-health.sqlite3"
    )
    unit_of_work_factory = build_unit_of_work_factory(
        build_session_factory(database_url)
    )
    with unit_of_work_factory() as unit_of_work:
        for index in range(1, 6):
            unit_of_work.events.add(
                replace(
                    commercial_event(
                        f"health-event-{index}",
                        external_reference=f"health-external-{index}",
                    ),
                    source="source-b" if index == 4 else "source-a",
                )
            )
        unit_of_work.processing_runs.add(
            replace(
                processing_run("health-run-2", "health-event-2"),
                started_at=datetime(2026, 7, 1, 0, tzinfo=UTC),
                completed_at=datetime(2026, 7, 1, 0, 1, tzinfo=UTC),
                final_status="posted",
                rules_engine_version="rules-1",
            )
        )
        unit_of_work.processing_runs.add(
            replace(
                processing_run("health-run-3a", "health-event-3"),
                started_at=datetime(2026, 7, 15, 0, tzinfo=UTC),
                completed_at=datetime(2026, 7, 15, 0, 1, tzinfo=UTC),
                final_status="not_evaluable",
                rules_engine_version="rules-1",
                phase_results=[
                    {
                        "phase": "classification",
                        "status": "completed",
                        "can_continue": True,
                    }
                ],
            )
        )
        unit_of_work.processing_runs.add(
            replace(
                processing_run("health-run-3b", "health-event-3"),
                started_at=datetime(2026, 7, 31, 23, tzinfo=UTC),
                completed_at=datetime(2026, 7, 31, 23, 1, tzinfo=UTC),
                final_status="posted",
                rules_engine_version="rules-2",
            )
        )
        unit_of_work.processing_runs.add(
            replace(
                processing_run("health-run-4", "health-event-4"),
                final_status="not_evaluable",
                rules_engine_version="rules-2",
            )
        )
        unit_of_work.ledger.add(
            replace(ledger_entry("health-ledger-2", "health-event-2"))
        )
        unit_of_work.ledger.add(
            replace(ledger_entry("health-ledger-3", "health-event-3"))
        )
        unit_of_work.commit()

    complete = request(application, "GET", "/processing/health")
    source = request(
        application, "GET", "/processing/health?source=source-a"
    )
    period = request(
        application,
        "GET",
        "/processing/health?start_date=2026-07-01&end_date=2026-07-31",
    )
    version = request(
        application,
        "GET",
        "/processing/health?rules_engine_version=rules-2",
    )
    empty = request(
        application,
        "GET",
        "/processing/health?start_date=2025-01-01&end_date=2025-01-31",
    )
    run_details = request(
        application, "GET", "/processing-runs/health-run-3a"
    )
    event_details = request(
        application, "GET", "/commercial-events/health-event-3"
    )

    assert complete.status_code == source.status_code == period.status_code == 200
    assert complete.json()["processing_runs"]["total"] == 4
    assert complete.json()["processing_runs"]["by_final_status"] == [
        {"final_status": "not_evaluable", "count": 2},
        {"final_status": "posted", "count": 2},
    ]
    assert complete.json()["processing_runs"]["by_rules_engine_version"] == [
        {"rules_engine_version": "rules-1", "count": 2},
        {"rules_engine_version": "rules-2", "count": 2},
    ]
    assert complete.json()["commercial_events"] == {
        "events_with_processing_runs": 3,
        "events_without_processing_runs": 2,
        "events_with_multiple_processing_runs": 1,
        "events_with_ledger_entries": 2,
        "events_without_ledger_entries": 3,
    }
    assert source.json()["processing_runs"]["total"] == 3
    assert source.json()["commercial_events"]["events_without_processing_runs"] == 2
    assert period.json()["processing_runs"]["total"] == 4
    assert period.json()["commercial_events"]["events_without_processing_runs"] == 0
    assert version.json()["processing_runs"]["total"] == 2
    assert version.json()["commercial_events"]["events_with_processing_runs"] == 2
    assert empty.json()["processing_runs"]["total"] == 0
    assert empty.json()["commercial_events"]["events_without_ledger_entries"] == 0
    assert run_details.status_code == event_details.status_code == 200
    assert len(event_details.json()["processing_runs"]) == 2

    after = request(application, "GET", "/processing/health")
    assert after.json() == complete.json()
    with unit_of_work_factory() as unit_of_work:
        assert len(
            unit_of_work.processing_runs.find_by_event_id("health-event-3")
        ) == 2
        assert len(unit_of_work.ledger.find_by_event_id("health-event-3")) == 1
    assert "raw_payload" not in complete.text
    assert "phase_results" not in complete.text
    engine.dispose()
