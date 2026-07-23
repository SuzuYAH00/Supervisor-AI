from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy"]


class CsvParsingResponse(BaseModel):
    total_data_rows: int
    converted_rows: int
    error_rows: int
    ignored_empty_rows: int


class CsvProcessingResponse(BaseModel):
    total_documents: int
    successful_documents: int
    validation_errors: int
    business_conflicts: int
    technical_errors: int
    processing_runs_created: int
    ledger_entries_created: int


class CsvRowResponse(BaseModel):
    line_number: int
    document_identifier: str | None
    status: str
    column: str | None = None
    commercial_event_id: str | None = None
    processing_run_id: str | None = None
    ledger_entry_id: str | None = None
    event_persisted: bool | None = None
    ledger_persisted: bool | None = None
    ledger_already_existed: bool | None = None
    final_status: str | None = None
    execution_duration_seconds: float | None = None
    error_type: str | None = None
    error_message: str | None = None


class CsvImportResponse(BaseModel):
    file: str
    status: Literal["success", "partial_failure"]
    parsing: CsvParsingResponse
    processing: CsvProcessingResponse
    duration_seconds: float
    started_at: str
    completed_at: str
    results: list[CsvRowResponse]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
