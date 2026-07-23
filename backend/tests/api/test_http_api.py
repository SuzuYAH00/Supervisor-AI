import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from supervisor_ai.api.app import (
    create_application_from_environment,
    create_http_application,
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
    application = create_http_application(service)
    response = request(application, "GET", "/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert service.calls == 0


def test_missing_empty_and_invalid_encoding_uploads_return_422() -> None:
    service = StubService(successful_result())
    application = create_http_application(service)
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
    response = upload(create_http_application(service), b"invalid\n")
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
        create_http_application(StubService(successful_result())),
        csv_text([csv_row()]).encode(),
        name="C:\\fakepath\\commercial.csv",
    )
    partial = upload(
        create_http_application(StubService(partial_result())),
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
        create_http_application(service),
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
        create_http_application(service),
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
        create_http_application(StubService(successful_result())),
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
