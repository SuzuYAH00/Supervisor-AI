import os
from datetime import date
from decimal import Decimal
from typing import Annotated, Protocol

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from supervisor_ai.api.schemas import (
    CollaboratorCurrencySummaryResponse,
    CollaboratorFinancialSummaryResponse,
    CsvImportResponse,
    ErrorResponse,
    FinancialSnapshotFiltersResponse,
    FinancialSnapshotItemResponse,
    FinancialSnapshotResponse,
    FinancialSnapshotTotalResponse,
    FinancialSummaryResponse,
    HealthResponse,
)
from supervisor_ai.application.use_cases import (
    GetFinancialSnapshotQuery,
    GetFinancialSnapshotResult,
    GetFinancialSummaryQuery,
    GetFinancialSummaryResult,
)
from supervisor_ai.infrastructure.importing import (
    CsvBatchImportResult,
    CsvStructureError,
)
from supervisor_ai.infrastructure.importing.reporting import (
    project_csv_import_report,
)

DATABASE_URL_ENV = "SUPERVISOR_AI_DATABASE_URL"


class CsvImportServiceContract(Protocol):
    def import_csv(self, content: str) -> CsvBatchImportResult: ...


class FinancialSnapshotServiceContract(Protocol):
    def execute(
        self, query: GetFinancialSnapshotQuery
    ) -> GetFinancialSnapshotResult: ...


class FinancialSummaryServiceContract(Protocol):
    def execute(self, query: GetFinancialSummaryQuery) -> GetFinancialSummaryResult: ...


def create_http_application(
    csv_import_service: CsvImportServiceContract,
    financial_snapshot_service: FinancialSnapshotServiceContract,
    financial_summary_service: FinancialSummaryServiceContract,
) -> FastAPI:
    app = FastAPI(
        title="Supervisor AI",
        description="API HTTP para importação operacional do Supervisor AI.",
        version="0.1.0",
    )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        del error
        if request.url.path == "/imports/csv":
            return _error_response(
                422,
                "upload_validation_error",
                "A CSV file is required in multipart field 'file'",
            )
        return _error_response(
            422,
            "invalid_query_parameters",
            "Financial query parameters are invalid",
        )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="healthy")

    @app.post(
        "/imports/csv",
        response_model=CsvImportResponse,
        responses={
            400: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        tags=["imports"],
    )
    async def import_csv(
        file: Annotated[UploadFile, File()],
    ) -> CsvImportResponse | JSONResponse:
        if not file.filename:
            return _error_response(422, "invalid_upload", "CSV filename is required")
        try:
            content_bytes = await file.read()
        except Exception:
            return _error_response(
                500,
                "upload_read_error",
                "CSV upload could not be read",
            )
        if not content_bytes:
            return _error_response(422, "empty_upload", "CSV file must not be empty")
        try:
            content = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            return _error_response(
                422,
                "invalid_encoding",
                "CSV file must use UTF-8 encoding",
            )
        try:
            result = csv_import_service.import_csv(content)
        except CsvStructureError:
            return _error_response(
                400,
                "csv_structure_error",
                "CSV structure is invalid",
            )
        except Exception:
            return _error_response(
                500,
                "internal_error",
                "CSV import could not be completed",
            )
        file_name = _safe_file_name(file.filename)
        return CsvImportResponse.model_validate(
            project_csv_import_report(file_name, result)
        )

    @app.get(
        "/financial/snapshot",
        response_model=FinancialSnapshotResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        tags=["financial"],
        summary="Consulta os créditos financeiros consolidados",
        description=(
            "Filtra créditos pela data UTC inclusiva de postagem. Valores "
            "monetários são strings decimais."
        ),
    )
    async def financial_snapshot(
        collaborator_id: Annotated[str | None, Query(min_length=1)] = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> FinancialSnapshotResponse | JSONResponse:
        try:
            query = GetFinancialSnapshotQuery(
                collaborator_id=collaborator_id,
                start_date=start_date,
                end_date=end_date,
            )
        except ValueError:
            return _error_response(
                422,
                "invalid_date_range",
                "start_date must not be after end_date",
            )
        try:
            result = financial_snapshot_service.execute(query)
        except Exception:
            return _error_response(
                500,
                "internal_error",
                "Financial snapshot could not be generated",
            )
        return _financial_snapshot_response(result)

    @app.get(
        "/financial/summary",
        response_model=FinancialSummaryResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        tags=["financial"],
        summary="Resume créditos financeiros por colaborador",
        description=(
            "Agrupa créditos por colaborador e moeda, com ranking e participação "
            "percentual. As datas UTC de postagem são inclusivas."
        ),
    )
    async def financial_summary(
        collaborator_id: Annotated[str | None, Query(min_length=1)] = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> FinancialSummaryResponse | JSONResponse:
        try:
            query = GetFinancialSummaryQuery(
                collaborator_id=collaborator_id,
                start_date=start_date,
                end_date=end_date,
            )
        except ValueError:
            return _error_response(
                422,
                "invalid_date_range",
                "start_date must not be after end_date",
            )
        try:
            result = financial_summary_service.execute(query)
        except Exception:
            return _error_response(
                500,
                "internal_error",
                "Financial summary could not be generated",
            )
        return _financial_summary_response(result)

    return app


def create_application_from_environment() -> FastAPI:
    database_url = os.environ.get(DATABASE_URL_ENV)
    if not database_url:
        raise RuntimeError(f"{DATABASE_URL_ENV} is required")
    from supervisor_ai.bootstrap import build_http_application

    return build_http_application(database_url)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _safe_file_name(value: str) -> str:
    return value.replace("\\", "/").rsplit("/", 1)[-1]


def _financial_snapshot_response(
    result: GetFinancialSnapshotResult,
) -> FinancialSnapshotResponse:
    return FinancialSnapshotResponse(
        filters=FinancialSnapshotFiltersResponse(
            collaborator_id=result.filters.collaborator_id,
            start_date=result.filters.start_date,
            end_date=result.filters.end_date,
        ),
        credit_count=result.credit_count,
        totals_by_currency=[
            FinancialSnapshotTotalResponse(
                currency=total.currency.value,
                amount=_decimal_string(total.amount),
            )
            for total in result.totals_by_currency
        ],
        items=[
            FinancialSnapshotItemResponse(
                ledger_entry_id=item.ledger_entry_id,
                commercial_event_id=item.commercial_event_id,
                collaborator_id=item.collaborator_id,
                amount=_decimal_string(item.amount),
                currency=item.currency.value,
                posted_at=item.posted_at,
                entry_type=item.entry_type.value,
                invoice_id=item.invoice_id,
            )
            for item in result.items
        ],
    )


def _decimal_string(value: Decimal) -> str:
    whole, separator, fraction = format(value, "f").partition(".")
    if not separator:
        return f"{whole}.00"
    significant = fraction.rstrip("0")
    return f"{whole}.{significant.ljust(2, '0')}"


def _financial_summary_response(
    result: GetFinancialSummaryResult,
) -> FinancialSummaryResponse:
    return FinancialSummaryResponse(
        filters=FinancialSnapshotFiltersResponse(
            collaborator_id=result.filters.collaborator_id,
            start_date=result.filters.start_date,
            end_date=result.filters.end_date,
        ),
        collaborator_count=result.collaborator_count,
        credit_count=result.credit_count,
        totals_by_currency=[
            FinancialSnapshotTotalResponse(
                currency=total.currency.value,
                amount=_decimal_string(total.amount),
            )
            for total in result.totals_by_currency
        ],
        collaborators=[
            CollaboratorFinancialSummaryResponse(
                collaborator_id=collaborator.collaborator_id,
                credit_count=collaborator.credit_count,
                totals_by_currency=[
                    CollaboratorCurrencySummaryResponse(
                        currency=total.currency.value,
                        amount=_decimal_string(total.amount),
                        credit_count=total.credit_count,
                        rank=total.rank,
                        share_percentage=_decimal_string(total.share_percentage),
                    )
                    for total in collaborator.totals_by_currency
                ],
            )
            for collaborator in result.collaborators
        ],
    )
