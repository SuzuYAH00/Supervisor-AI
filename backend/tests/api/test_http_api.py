import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from supervisor_ai.api.app import (
    HttpApplicationServices,
    create_application_from_environment,
    create_http_application,
)
from supervisor_ai.api.pagination import (
    decode_cursor,
    encode_cursor,
    encode_timeline_cursor,
)
from supervisor_ai.application import (
    CollaboratorFinancialTimelineCursorPosition,
    CommercialEventCursorPosition,
    CommercialEventNotFound,
)
from supervisor_ai.application.use_cases import (
    CollaboratorCurrencySummary,
    CollaboratorFinancialSummary,
    CollaboratorFinancialTimelineItem,
    CommercialEventDetails,
    CommercialEventLedgerEntry,
    CommercialEventListItem,
    CommercialEventProcessingRun,
    FinancialSnapshotCurrencyTotal,
    FinancialSnapshotItem,
    FinancialSummaryCurrencyTotal,
    GetCollaboratorFinancialTimelineQuery,
    GetCollaboratorFinancialTimelineResult,
    GetCommercialEventDetailsQuery,
    GetCommercialEventDetailsResult,
    GetFinancialSnapshotQuery,
    GetFinancialSnapshotResult,
    GetFinancialSummaryQuery,
    GetFinancialSummaryResult,
    ListCommercialEventsQuery,
    ListCommercialEventsResult,
    TimelineCommercialEvent,
)
from supervisor_ai.infrastructure.importing import (
    BatchDocumentResult,
    BatchDocumentStatus,
    BatchImportResult,
    BatchStatistics,
    CsvBatchImportResult,
    CsvImportAdapter,
    CsvStructureError,
)
from supervisor_ai.rules_engine import Currency, LedgerEntryType
from tests.importing.csv_factories import csv_row, csv_text

NOW = datetime(2026, 7, 22, 15, 0, tzinfo=UTC)


class StubService:
    def __init__(
        self,
        result: CsvBatchImportResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    def import_csv(self, content: str) -> CsvBatchImportResult:
        self.calls += 1
        assert content
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


class StubFinancialService:
    def __init__(
        self,
        result: GetFinancialSnapshotResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.queries: list[GetFinancialSnapshotQuery] = []

    def execute(
        self, query: GetFinancialSnapshotQuery
    ) -> GetFinancialSnapshotResult:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.result or GetFinancialSnapshotResult(query, 0, (), ())


class StubFinancialSummaryService:
    def __init__(
        self,
        result: GetFinancialSummaryResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.queries: list[GetFinancialSummaryQuery] = []

    def execute(self, query: GetFinancialSummaryQuery) -> GetFinancialSummaryResult:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.result or GetFinancialSummaryResult(query, 0, 0, (), ())


class StubCommercialEventDetailsService:
    def __init__(
        self,
        result: GetCommercialEventDetailsResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.queries: list[GetCommercialEventDetailsQuery] = []

    def execute(
        self, query: GetCommercialEventDetailsQuery
    ) -> GetCommercialEventDetailsResult:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


class StubCommercialEventListService:
    def __init__(
        self,
        result: ListCommercialEventsResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.queries: list[ListCommercialEventsQuery] = []

    def execute(self, query: ListCommercialEventsQuery) -> ListCommercialEventsResult:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.result or ListCommercialEventsResult(query, (), False, None)


class StubCollaboratorTimelineService:
    def __init__(
        self,
        result: GetCollaboratorFinancialTimelineResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.queries: list[GetCollaboratorFinancialTimelineQuery] = []

    def execute(
        self, query: GetCollaboratorFinancialTimelineQuery
    ) -> GetCollaboratorFinancialTimelineResult:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.result or GetCollaboratorFinancialTimelineResult(
            query, (), False, None
        )


def _application(
    service: StubService,
    financial_service: StubFinancialService | None = None,
    summary_service: StubFinancialSummaryService | None = None,
    details_service: StubCommercialEventDetailsService | None = None,
    list_service: StubCommercialEventListService | None = None,
    timeline_service: StubCollaboratorTimelineService | None = None,
) -> FastAPI:
    return create_http_application(
        HttpApplicationServices(
            csv_import=service,
            financial_snapshot=financial_service or StubFinancialService(),
            financial_summary=summary_service or StubFinancialSummaryService(),
            commercial_event_details=(
                details_service or StubCommercialEventDetailsService()
            ),
            commercial_event_list=list_service or StubCommercialEventListService(),
            collaborator_financial_timeline=(
                timeline_service or StubCollaboratorTimelineService()
            ),
        )
    )


def successful_result() -> CsvBatchImportResult:
    parsing = CsvImportAdapter().parse(csv_text([csv_row()]))
    item = BatchDocumentResult(
        document_identifier="csv-row-1",
        processing_status=BatchDocumentStatus.SUCCESS,
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        execution_duration=timedelta(seconds=1),
        processing_run_id="run-1",
        commercial_event_id="event-csv-1",
        ledger_entry_id="ledger-1",
        final_status="posted",
        event_persisted=True,
        ledger_persisted=True,
    )
    batch = BatchImportResult(
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        processing_duration=timedelta(seconds=1),
        statistics=BatchStatistics.from_results((item,)),
        ordered_results=(item,),
    )
    return CsvBatchImportResult(parsing=parsing, batch=batch)


def partial_result() -> CsvBatchImportResult:
    valid = csv_row(1)
    invalid = csv_row(2)
    invalid["invoice_recurring_amount"] = "99,90"
    parsing = CsvImportAdapter().parse(csv_text([valid, invalid]))
    item = BatchDocumentResult(
        document_identifier="csv-row-1",
        processing_status=BatchDocumentStatus.BUSINESS_CONFLICT,
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        execution_duration=timedelta(seconds=1),
        error_type="CommercialEventConflict",
        error_message="external reference reused",
    )
    batch = BatchImportResult(
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        processing_duration=timedelta(seconds=1),
        statistics=BatchStatistics.from_results((item,)),
        ordered_results=(item,),
    )
    return CsvBatchImportResult(parsing=parsing, batch=batch)


def request(
    application: FastAPI,
    method: str,
    path: str,
    *,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> Response:
    async def execute() -> Response:
        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.request(method, path, files=files)

    return asyncio.run(execute())


def upload(application: FastAPI, content: bytes, name: str = "commercial.csv"):
    return request(
        application,
        "POST",
        "/imports/csv",
        files={"file": (name, content, "text/csv")},
    )


def test_health_is_process_only_and_does_not_call_service() -> None:
    service = StubService(error=AssertionError("must not be called"))
    application = _application(service)
    response = request(application, "GET", "/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert service.calls == 0


def test_missing_empty_and_invalid_encoding_uploads_return_422() -> None:
    service = StubService(successful_result())
    application = _application(service)
    missing = request(application, "POST", "/imports/csv")
    empty = upload(application, b"")
    invalid = upload(application, b"\xff\xfe")
    assert missing.status_code == empty.status_code == invalid.status_code == 422
    assert missing.json()["error"]["code"] == "upload_validation_error"
    assert empty.json()["error"]["code"] == "empty_upload"
    assert invalid.json()["error"]["code"] == "invalid_encoding"
    assert service.calls == 0


def test_invalid_global_structure_returns_safe_400() -> None:
    service = StubService(error=CsvStructureError("secret header detail"))
    response = upload(_application(service), b"invalid\n")
    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "csv_structure_error",
            "message": "CSV structure is invalid",
        }
    }
    assert "secret" not in response.text


def test_valid_and_partial_imports_both_return_200() -> None:
    success = upload(
        _application(StubService(successful_result())),
        csv_text([csv_row()]).encode(),
        name="C:\\fakepath\\commercial.csv",
    )
    partial = upload(
        _application(StubService(partial_result())),
        csv_text([csv_row()]).encode(),
    )
    assert success.status_code == partial.status_code == 200
    assert success.json()["status"] == "success"
    assert success.json()["file"] == "commercial.csv"
    assert partial.json()["status"] == "partial_failure"
    assert [item["line_number"] for item in partial.json()["results"]] == [2, 3]


def test_utf8_bom_upload_is_accepted() -> None:
    service = StubService(successful_result())
    response = upload(
        _application(service),
        csv_text([csv_row()]).encode("utf-8-sig"),
    )
    assert response.status_code == 200
    assert service.calls == 1


def test_unexpected_failure_returns_safe_500_without_sensitive_details() -> None:
    service = StubService(
        error=RuntimeError(
            "postgresql://user:password@database raw_payload Traceback SQLAlchemy"
        )
    )
    response = upload(
        _application(service),
        csv_text([csv_row()]).encode(),
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    for sensitive in (
        "raw_payload",
        "password",
        "Traceback",
        "SQLAlchemy",
        "postgresql",
    ):
        assert sensitive not in response.text


def test_http_projection_never_exposes_transport_or_configuration_data() -> None:
    response = upload(
        _application(StubService(successful_result())),
        csv_text([csv_row()]).encode(),
    )
    assert response.status_code == 200
    assert "raw_payload" not in response.text
    assert "database_url" not in response.text
    assert "sqlite" not in response.text


def test_environment_factory_requires_explicit_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPERVISOR_AI_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="SUPERVISOR_AI_DATABASE_URL"):
        create_application_from_environment()


def financial_result(query: GetFinancialSnapshotQuery) -> GetFinancialSnapshotResult:
    item = FinancialSnapshotItem(
        ledger_entry_id="ledger-1",
        commercial_event_id="event-1",
        collaborator_id="collaborator-1",
        amount=Decimal("119.900000"),
        currency=Currency.BRL,
        posted_at=datetime(2026, 7, 20, 13, tzinfo=UTC),
        entry_type=LedgerEntryType.CREDIT,
        invoice_id="invoice-1",
    )
    return GetFinancialSnapshotResult(
        filters=query,
        credit_count=1,
        totals_by_currency=(
            FinancialSnapshotCurrencyTotal(Currency.BRL, Decimal("119.900000")),
        ),
        items=(item,),
    )


def test_financial_snapshot_returns_complete_and_empty_views() -> None:
    query = GetFinancialSnapshotQuery()
    populated_service = StubFinancialService(financial_result(query))
    populated = request(
        _application(StubService(), populated_service),
        "GET",
        "/financial/snapshot",
    )
    empty = request(
        _application(StubService(), StubFinancialService()),
        "GET",
        "/financial/snapshot",
    )
    assert populated.status_code == empty.status_code == 200
    assert populated.json()["credit_count"] == 1
    assert populated.json()["totals_by_currency"] == [
        {"currency": "BRL", "amount": "119.90"}
    ]
    assert populated.json()["items"][0]["amount"] == "119.90"
    assert type(populated.json()["items"][0]["amount"]) is str
    assert empty.json()["credit_count"] == 0
    assert empty.json()["totals_by_currency"] == []
    assert empty.json()["items"] == []


@pytest.mark.parametrize(
    "query_string",
    [
        "collaborator_id=collaborator-1",
        "start_date=2026-07-01&end_date=2026-07-31",
        (
            "collaborator_id=collaborator-1&start_date=2026-07-01"
            "&end_date=2026-07-31"
        ),
    ],
)
def test_financial_snapshot_forwards_supported_filters(query_string: str) -> None:
    service = StubFinancialService()
    response = request(
        _application(StubService(), service),
        "GET",
        f"/financial/snapshot?{query_string}",
    )
    assert response.status_code == 200
    assert len(service.queries) == 1
    assert response.json()["filters"] == {
        "collaborator_id": service.queries[0].collaborator_id,
        "start_date": (
            None
            if service.queries[0].start_date is None
            else service.queries[0].start_date.isoformat()
        ),
        "end_date": (
            None
            if service.queries[0].end_date is None
            else service.queries[0].end_date.isoformat()
        ),
    }


@pytest.mark.parametrize(
    "query_string",
    ["start_date=invalid", "end_date=2026-02-30"],
)
def test_invalid_financial_dates_return_route_specific_422(
    query_string: str,
) -> None:
    response = request(
        _application(StubService()),
        "GET",
        f"/financial/snapshot?{query_string}",
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_query_parameters"
    assert "CSV file" not in response.text


def test_inverted_financial_interval_returns_specific_422() -> None:
    response = request(
        _application(StubService()),
        "GET",
        "/financial/snapshot?start_date=2026-08-01&end_date=2026-07-31",
    )
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_date_range",
            "message": "start_date must not be after end_date",
        }
    }


def test_financial_failure_returns_safe_500() -> None:
    service = StubFinancialService(
        error=RuntimeError(
            "postgresql://user:password raw_payload Traceback SQLAlchemy"
        )
    )
    response = request(
        _application(StubService(), service),
        "GET",
        "/financial/snapshot",
    )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Financial snapshot could not be generated",
        }
    }
    for sensitive in (
        "raw_payload",
        "password",
        "Traceback",
        "SQLAlchemy",
        "postgresql",
    ):
        assert sensitive not in response.text


def summary_result(query: GetFinancialSummaryQuery) -> GetFinancialSummaryResult:
    return GetFinancialSummaryResult(
        filters=query,
        collaborator_count=2,
        credit_count=3,
        totals_by_currency=(
            FinancialSummaryCurrencyTotal(Currency.BRL, Decimal("300.000000")),
            FinancialSummaryCurrencyTotal(Currency.USD, Decimal("25.500000")),
        ),
        collaborators=(
            CollaboratorFinancialSummary(
                collaborator_id="alice",
                credit_count=2,
                totals_by_currency=(
                    CollaboratorCurrencySummary(
                        Currency.BRL,
                        Decimal("200.000000"),
                        2,
                        1,
                        Decimal("66.67"),
                    ),
                ),
            ),
            CollaboratorFinancialSummary(
                collaborator_id="bob",
                credit_count=1,
                totals_by_currency=(
                    CollaboratorCurrencySummary(
                        Currency.BRL,
                        Decimal("100.000000"),
                        1,
                        2,
                        Decimal("33.33"),
                    ),
                    CollaboratorCurrencySummary(
                        Currency.USD,
                        Decimal("25.500000"),
                        1,
                        1,
                        Decimal("100.00"),
                    ),
                ),
            ),
        ),
    )


def test_financial_summary_returns_stable_decimal_projection_and_empty_view() -> None:
    query = GetFinancialSummaryQuery()
    populated = request(
        _application(
            StubService(),
            summary_service=StubFinancialSummaryService(summary_result(query)),
        ),
        "GET",
        "/financial/summary",
    )
    empty = request(_application(StubService()), "GET", "/financial/summary")
    assert populated.status_code == empty.status_code == 200
    body = populated.json()
    assert body["collaborator_count"] == 2
    assert body["credit_count"] == 3
    assert body["totals_by_currency"] == [
        {"currency": "BRL", "amount": "300.00"},
        {"currency": "USD", "amount": "25.50"},
    ]
    assert body["collaborators"][0]["totals_by_currency"][0] == {
        "currency": "BRL",
        "amount": "200.00",
        "credit_count": 2,
        "rank": 1,
        "share_percentage": "66.67",
    }
    assert type(body["totals_by_currency"][0]["amount"]) is str
    assert type(
        body["collaborators"][0]["totals_by_currency"][0]["share_percentage"]
    ) is str
    assert empty.json() == {
        "filters": {"collaborator_id": None, "start_date": None, "end_date": None},
        "collaborator_count": 0,
        "credit_count": 0,
        "totals_by_currency": [],
        "collaborators": [],
    }
    for sensitive in ("raw_payload", "database_url", "Traceback"):
        assert sensitive not in populated.text


@pytest.mark.parametrize(
    "query_string",
    [
        "collaborator_id=alice",
        "start_date=2026-07-01&end_date=2026-07-31",
        "collaborator_id=alice&start_date=2026-07-01&end_date=2026-07-31",
    ],
)
def test_financial_summary_forwards_supported_filters(query_string: str) -> None:
    service = StubFinancialSummaryService()
    response = request(
        _application(StubService(), summary_service=service),
        "GET",
        f"/financial/summary?{query_string}",
    )
    assert response.status_code == 200
    assert len(service.queries) == 1
    assert response.json()["filters"]["collaborator_id"] == (
        service.queries[0].collaborator_id
    )


def test_financial_summary_rejects_invalid_dates_and_inverted_interval() -> None:
    invalid = request(
        _application(StubService()),
        "GET",
        "/financial/summary?start_date=invalid",
    )
    inverted = request(
        _application(StubService()),
        "GET",
        "/financial/summary?start_date=2026-08-01&end_date=2026-07-31",
    )
    assert invalid.status_code == inverted.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_query_parameters"
    assert "CSV file" not in invalid.text
    assert inverted.json()["error"]["code"] == "invalid_date_range"


def test_financial_summary_failure_returns_safe_500() -> None:
    service = StubFinancialSummaryService(
        error=RuntimeError("postgresql password raw_payload Traceback SQLAlchemy")
    )
    response = request(
        _application(StubService(), summary_service=service),
        "GET",
        "/financial/summary",
    )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Financial summary could not be generated",
        }
    }
    for sensitive in ("raw_payload", "password", "Traceback", "SQLAlchemy"):
        assert sensitive not in response.text


def commercial_event_details_result() -> GetCommercialEventDetailsResult:
    return GetCommercialEventDetailsResult(
        commercial_event=CommercialEventDetails(
            event_id="event-1",
            external_reference="external-1",
            source="csv",
            occurred_at=NOW,
            received_at=NOW + timedelta(minutes=1),
            created_at=NOW + timedelta(minutes=2),
        ),
        ledger_entries=(
            CommercialEventLedgerEntry(
                ledger_entry_id="ledger-1",
                event_id="event-1",
                beneficiary_id="alice",
                entry_type=LedgerEntryType.CREDIT,
                amount=Decimal("119.900000"),
                currency=Currency.BRL,
                posted_at=NOW + timedelta(minutes=5),
                posting_reference="posting-1",
                remuneration_calculation_reference="calculation-1",
                invoice_id="invoice-1",
                source_reference_ids=("ticket-1", "invoice-1"),
            ),
        ),
        processing_runs=(
            CommercialEventProcessingRun(
                processing_run_id="run-1",
                event_id="event-1",
                final_status="posted",
                started_at=NOW + timedelta(minutes=3),
                completed_at=NOW + timedelta(minutes=4),
                rules_engine_version="rules-1",
                created_at=NOW + timedelta(minutes=3),
            ),
        ),
    )


def test_commercial_event_details_returns_explicit_safe_projection() -> None:
    service = StubCommercialEventDetailsService(commercial_event_details_result())
    response = request(
        _application(StubService(), details_service=service),
        "GET",
        "/commercial-events/event-1",
    )
    assert response.status_code == 200
    assert service.queries == [GetCommercialEventDetailsQuery("event-1")]
    body = response.json()
    assert body["commercial_event"] == {
        "event_id": "event-1",
        "external_reference": "external-1",
        "source": "csv",
        "occurred_at": "2026-07-22T15:00:00Z",
        "received_at": "2026-07-22T15:01:00Z",
        "created_at": "2026-07-22T15:02:00Z",
    }
    assert body["ledger_entries"][0]["amount"] == "119.90"
    assert type(body["ledger_entries"][0]["amount"]) is str
    assert body["ledger_entries"][0]["entry_type"] == "credit"
    for sensitive in (
        "raw_payload",
        "database_url",
        "password",
        "Traceback",
        "SQLAlchemy",
    ):
        assert sensitive not in response.text


def test_commercial_event_details_supports_empty_related_histories() -> None:
    original = commercial_event_details_result()
    service = StubCommercialEventDetailsService(
        GetCommercialEventDetailsResult(original.commercial_event, (), ())
    )
    response = request(
        _application(StubService(), details_service=service),
        "GET",
        "/commercial-events/event-1",
    )
    assert response.status_code == 200
    assert response.json()["ledger_entries"] == []
    assert response.json()["processing_runs"] == []


def test_commercial_event_details_maps_not_found_to_stable_404() -> None:
    service = StubCommercialEventDetailsService(
        error=CommercialEventNotFound("missing")
    )
    response = request(
        _application(StubService(), details_service=service),
        "GET",
        "/commercial-events/missing",
    )
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "commercial_event_not_found",
            "message": "Commercial event was not found",
        }
    }


@pytest.mark.parametrize("event_id", ["%20%20", "x" * 129])
def test_commercial_event_details_rejects_invalid_identifier(event_id: str) -> None:
    response = request(
        _application(StubService()),
        "GET",
        f"/commercial-events/{event_id}",
    )
    assert response.status_code == 422
    assert "CSV file" not in response.text


def test_commercial_event_details_failure_returns_safe_500() -> None:
    service = StubCommercialEventDetailsService(
        error=RuntimeError("postgresql password raw_payload Traceback SQLAlchemy")
    )
    response = request(
        _application(StubService(), details_service=service),
        "GET",
        "/commercial-events/event-1",
    )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Commercial event details could not be retrieved",
        }
    }
    for sensitive in ("raw_payload", "password", "Traceback", "SQLAlchemy"):
        assert sensitive not in response.text


def commercial_event_list_result(
    query: ListCommercialEventsQuery,
    *,
    has_more: bool = True,
) -> ListCommercialEventsResult:
    item = CommercialEventListItem(
        event_id="event-2",
        external_reference="external-2",
        source="csv",
        occurred_at=NOW,
        received_at=NOW + timedelta(minutes=1),
        created_at=NOW + timedelta(minutes=2),
    )
    return ListCommercialEventsResult(
        filters=query,
        items=(item,),
        has_more=has_more,
        next_cursor_position=(
            CommercialEventCursorPosition(item.occurred_at, item.event_id)
            if has_more
            else None
        ),
    )


def test_commercial_event_list_returns_public_items_and_cursor() -> None:
    query = ListCommercialEventsQuery(limit=1)
    service = StubCommercialEventListService(commercial_event_list_result(query))
    response = request(
        _application(StubService(), list_service=service),
        "GET",
        "/commercial-events?limit=1",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filters"] == {
        "source": None,
        "external_reference": None,
        "start_date": None,
        "end_date": None,
    }
    assert body["page"]["limit"] == 1
    assert body["page"]["has_more"] is True
    assert decode_cursor(body["page"]["next_cursor"]) == (
        CommercialEventCursorPosition(NOW, "event-2")
    )
    assert body["items"] == [
        {
            "event_id": "event-2",
            "external_reference": "external-2",
            "source": "csv",
            "occurred_at": "2026-07-22T15:00:00Z",
            "received_at": "2026-07-22T15:01:00Z",
            "created_at": "2026-07-22T15:02:00Z",
        }
    ]
    for absent in ("raw_payload", "ledger_entries", "processing_runs"):
        assert absent not in response.text


def test_commercial_event_list_empty_response_uses_default_limit() -> None:
    response = request(_application(StubService()), "GET", "/commercial-events")
    assert response.status_code == 200
    assert response.json() == {
        "filters": {
            "source": None,
            "external_reference": None,
            "start_date": None,
            "end_date": None,
        },
        "page": {"limit": 50, "next_cursor": None, "has_more": False},
        "items": [],
    }


def test_commercial_event_list_forwards_filters_and_decoded_cursor() -> None:
    position = CommercialEventCursorPosition(NOW, "event-2")
    service = StubCommercialEventListService()
    cursor = encode_cursor(position)
    response = request(
        _application(StubService(), list_service=service),
        "GET",
        (
            "/commercial-events?source=csv&external_reference=external-2"
            "&start_date=2026-07-01&end_date=2026-07-31"
            f"&limit=25&cursor={cursor}"
        ),
    )
    assert response.status_code == 200
    assert service.queries == [
        ListCommercialEventsQuery(
            source="csv",
            external_reference="external-2",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            limit=25,
            after=position,
        )
    ]


@pytest.mark.parametrize(
    "query_string",
    [
        "limit=0",
        "limit=101",
        "source=%20%20",
        "external_reference=%20",
        "start_date=invalid",
        "start_date=2026-08-01&end_date=2026-07-31",
    ],
)
def test_commercial_event_list_rejects_invalid_filters(query_string: str) -> None:
    response = request(
        _application(StubService()),
        "GET",
        f"/commercial-events?{query_string}",
    )
    assert response.status_code == 422


def test_commercial_event_list_rejects_invalid_cursor_with_stable_error() -> None:
    response = request(
        _application(StubService()),
        "GET",
        "/commercial-events?cursor=not-valid***",
    )
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_cursor",
            "message": "Pagination cursor is invalid",
        }
    }


def test_commercial_event_list_failure_is_safe() -> None:
    service = StubCommercialEventListService(
        error=RuntimeError("postgresql password raw_payload Traceback SQLAlchemy")
    )
    response = request(
        _application(StubService(), list_service=service),
        "GET",
        "/commercial-events",
    )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Commercial events could not be retrieved",
        }
    }
    for sensitive in ("raw_payload", "password", "Traceback", "SQLAlchemy"):
        assert sensitive not in response.text


def timeline_result(
    query: GetCollaboratorFinancialTimelineQuery,
) -> GetCollaboratorFinancialTimelineResult:
    item = CollaboratorFinancialTimelineItem(
        ledger_entry_id="ledger-1",
        posted_at=NOW,
        entry_type=LedgerEntryType.CREDIT,
        amount=Decimal("99.900000"),
        currency=Currency.BRL,
        invoice_id="invoice-1",
        posting_reference="posting-1",
        remuneration_calculation_reference="calculation-1",
        source_reference_ids=("invoice-1",),
        commercial_event=TimelineCommercialEvent(
            event_id="event-1",
            external_reference="external-1",
            source="csv",
            occurred_at=NOW - timedelta(minutes=5),
        ),
    )
    return GetCollaboratorFinancialTimelineResult(
        query,
        (item,),
        True,
        CollaboratorFinancialTimelineCursorPosition(NOW, "ledger-1"),
    )


def test_collaborator_timeline_returns_explicit_decimal_projection() -> None:
    query = GetCollaboratorFinancialTimelineQuery("alice", limit=1)
    service = StubCollaboratorTimelineService(timeline_result(query))
    response = request(
        _application(StubService(), timeline_service=service),
        "GET",
        "/collaborators/alice/financial-timeline?limit=1",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["collaborator_id"] == "alice"
    assert body["page"]["has_more"] is True
    assert type(body["page"]["next_cursor"]) is str
    assert body["items"][0]["amount"] == "99.90"
    assert type(body["items"][0]["amount"]) is str
    assert body["items"][0]["entry_type"] == "credit"
    assert body["items"][0]["commercial_event"]["event_id"] == "event-1"
    for absent in ("raw_payload", "processing_runs", "database_url"):
        assert absent not in response.text


def test_collaborator_timeline_empty_is_200_with_default_limit() -> None:
    response = request(
        _application(StubService()),
        "GET",
        "/collaborators/unknown/financial-timeline",
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["page"] == {
        "limit": 50,
        "next_cursor": None,
        "has_more": False,
    }


def test_collaborator_timeline_forwards_filters_and_cursor() -> None:
    position = CollaboratorFinancialTimelineCursorPosition(NOW, "ledger-1")
    cursor = encode_timeline_cursor(position)
    service = StubCollaboratorTimelineService()
    response = request(
        _application(StubService(), timeline_service=service),
        "GET",
        (
            "/collaborators/alice/financial-timeline"
            "?start_date=2026-07-01&end_date=2026-07-31"
            f"&entry_type=credit&currency=BRL&limit=25&cursor={cursor}"
        ),
    )
    assert response.status_code == 200
    assert service.queries == [
        GetCollaboratorFinancialTimelineQuery(
            "alice",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            entry_type=LedgerEntryType.CREDIT,
            currency=Currency.BRL,
            limit=25,
            after=position,
        )
    ]


@pytest.mark.parametrize(
    "path",
    [
        "/collaborators/%20%20/financial-timeline",
        f"/collaborators/{'x' * 129}/financial-timeline",
        "/collaborators/alice/financial-timeline?limit=0",
        "/collaborators/alice/financial-timeline?entry_type=unknown",
        "/collaborators/alice/financial-timeline?currency=EUR",
        "/collaborators/alice/financial-timeline?start_date=invalid",
        (
            "/collaborators/alice/financial-timeline"
            "?start_date=2026-08-01&end_date=2026-07-31"
        ),
    ],
)
def test_collaborator_timeline_rejects_invalid_parameters(path: str) -> None:
    assert request(_application(StubService()), "GET", path).status_code == 422


def test_collaborator_timeline_maps_invalid_cursor_and_safe_failure() -> None:
    invalid = request(
        _application(StubService()),
        "GET",
        "/collaborators/alice/financial-timeline?cursor=invalid***",
    )
    service = StubCollaboratorTimelineService(
        error=RuntimeError("postgresql password raw_payload Traceback SQLAlchemy")
    )
    failed = request(
        _application(StubService(), timeline_service=service),
        "GET",
        "/collaborators/alice/financial-timeline",
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_cursor"
    assert failed.status_code == 500
    assert failed.json()["error"]["message"] == (
        "Collaborator financial timeline could not be retrieved"
    )
    for sensitive in ("password", "raw_payload", "Traceback", "SQLAlchemy"):
        assert sensitive not in failed.text
