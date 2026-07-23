import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from supervisor_ai.api.app import (
    create_application_from_environment,
    create_http_application,
)
from supervisor_ai.application.use_cases import (
    CollaboratorCurrencySummary,
    CollaboratorFinancialSummary,
    FinancialSnapshotCurrencyTotal,
    FinancialSnapshotItem,
    FinancialSummaryCurrencyTotal,
    GetFinancialSnapshotQuery,
    GetFinancialSnapshotResult,
    GetFinancialSummaryQuery,
    GetFinancialSummaryResult,
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


def _application(
    service: StubService,
    financial_service: StubFinancialService | None = None,
    summary_service: StubFinancialSummaryService | None = None,
) -> FastAPI:
    return create_http_application(
        service,
        financial_service or StubFinancialService(),
        summary_service or StubFinancialSummaryService(),
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
