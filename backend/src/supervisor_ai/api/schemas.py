from datetime import date, datetime
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


class FinancialSnapshotFiltersResponse(BaseModel):
    collaborator_id: str | None
    start_date: date | None
    end_date: date | None


class FinancialSnapshotTotalResponse(BaseModel):
    currency: str
    amount: str


class FinancialSnapshotItemResponse(BaseModel):
    ledger_entry_id: str
    commercial_event_id: str
    collaborator_id: str
    amount: str
    currency: str
    posted_at: datetime
    entry_type: str
    invoice_id: str | None


class FinancialSnapshotResponse(BaseModel):
    filters: FinancialSnapshotFiltersResponse
    credit_count: int
    totals_by_currency: list[FinancialSnapshotTotalResponse]
    items: list[FinancialSnapshotItemResponse]


class CollaboratorCurrencySummaryResponse(BaseModel):
    currency: str
    amount: str
    credit_count: int
    rank: int
    share_percentage: str


class CollaboratorFinancialSummaryResponse(BaseModel):
    collaborator_id: str
    credit_count: int
    totals_by_currency: list[CollaboratorCurrencySummaryResponse]


class FinancialSummaryResponse(BaseModel):
    filters: FinancialSnapshotFiltersResponse
    collaborator_count: int
    credit_count: int
    totals_by_currency: list[FinancialSnapshotTotalResponse]
    collaborators: list[CollaboratorFinancialSummaryResponse]


class CommercialEventResponse(BaseModel):
    event_id: str
    external_reference: str
    source: str
    occurred_at: datetime
    received_at: datetime
    created_at: datetime


class CommercialEventLedgerEntryResponse(BaseModel):
    ledger_entry_id: str
    event_id: str
    beneficiary_id: str
    entry_type: str
    amount: str
    currency: str
    posted_at: datetime
    posting_reference: str
    remuneration_calculation_reference: str
    invoice_id: str | None
    source_reference_ids: list[str]


class CommercialEventProcessingRunResponse(BaseModel):
    processing_run_id: str
    event_id: str
    final_status: str
    started_at: datetime
    completed_at: datetime
    rules_engine_version: str
    created_at: datetime


class CommercialEventDetailsResponse(BaseModel):
    commercial_event: CommercialEventResponse
    ledger_entries: list[CommercialEventLedgerEntryResponse]
    processing_runs: list[CommercialEventProcessingRunResponse]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
