import os
from typing import Annotated, Protocol

from fastapi import FastAPI, File, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

from supervisor_ai.api.schemas import (
    CsvImportResponse,
    ErrorResponse,
    HealthResponse,
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


def create_http_application(service: CsvImportServiceContract) -> FastAPI:
    app = FastAPI(
        title="Supervisor AI",
        description="API HTTP para importação operacional do Supervisor AI.",
        version="0.1.0",
    )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        del request, error
        return _error_response(
            422,
            "upload_validation_error",
            "A CSV file is required in multipart field 'file'",
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
            result = service.import_csv(content)
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
