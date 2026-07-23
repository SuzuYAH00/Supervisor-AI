from dataclasses import dataclass

from supervisor_ai.infrastructure.importing.batch import (
    BatchDocumentResult,
    BatchDocumentStatus,
)
from supervisor_ai.infrastructure.importing.csv_adapter import (
    CsvBatchImportResult,
    CsvRowResult,
)


@dataclass(frozen=True, slots=True)
class CorrelatedCsvRowResult:
    csv_row: CsvRowResult
    batch_result: BatchDocumentResult | None


def correlate_csv_rows(
    result: CsvBatchImportResult,
) -> tuple[CorrelatedCsvRowResult, ...]:
    by_identifier = {
        item.document_identifier: item for item in result.batch.ordered_results
    }
    return tuple(
        CorrelatedCsvRowResult(
            csv_row=row,
            batch_result=(
                None
                if row.document_identifier is None
                else by_identifier.get(row.document_identifier)
            ),
        )
        for row in result.parsing.rows
    )


def project_csv_import_report(
    file_name: str, result: CsvBatchImportResult
) -> dict[str, object]:
    parsing = result.parsing.statistics
    processing = result.batch.statistics
    projection: dict[str, object] = {
        "file": file_name,
        "status": "partial_failure" if has_csv_import_failures(result) else "success",
        "parsing": {
            "total_data_rows": parsing.total_data_rows,
            "converted_rows": parsing.converted_rows,
            "error_rows": parsing.error_rows,
            "ignored_empty_rows": parsing.ignored_empty_rows,
        },
        "processing": {
            "total_documents": processing.total_documents,
            "successful_documents": processing.successful_documents,
            "validation_errors": processing.validation_errors,
            "business_conflicts": processing.business_conflicts,
            "technical_errors": processing.technical_errors,
            "processing_runs_created": processing.processing_runs_created,
            "ledger_entries_created": processing.ledger_entries_created,
        },
        "duration_seconds": result.batch.processing_duration.total_seconds(),
        "started_at": result.batch.started_at.isoformat(),
        "completed_at": result.batch.completed_at.isoformat(),
        "results": [_project_row(item) for item in correlate_csv_rows(result)],
    }
    return projection


def has_csv_import_failures(result: CsvBatchImportResult) -> bool:
    parsing = result.parsing.statistics
    processing = result.batch.statistics
    return any(
        (
            parsing.error_rows,
            processing.validation_errors,
            processing.business_conflicts,
            processing.technical_errors,
        )
    )


def safe_batch_error_message(result: BatchDocumentResult) -> str | None:
    if result.processing_status is BatchDocumentStatus.TECHNICAL_ERROR:
        return "technical processing failure"
    return result.error_message


def _project_row(item: CorrelatedCsvRowResult) -> dict[str, object]:
    row = item.csv_row
    projection: dict[str, object] = {
        "line_number": row.line_number,
        "document_identifier": row.document_identifier,
    }
    if row.errors:
        error = row.errors[0]
        projection.update(
            {
                "status": error.category.value,
                "column": error.column,
                "error_type": "CsvRowError",
                "error_message": error.message,
            }
        )
        return projection
    batch = item.batch_result
    if batch is None:
        projection.update(
            {
                "status": "technical_error",
                "error_type": "MissingBatchResult",
                "error_message": "batch result is missing",
            }
        )
        return projection
    projection.update(
        {
            "status": batch.processing_status.value,
            "commercial_event_id": batch.commercial_event_id,
            "processing_run_id": batch.processing_run_id,
            "ledger_entry_id": batch.ledger_entry_id,
            "event_persisted": batch.event_persisted,
            "ledger_persisted": batch.ledger_persisted,
            "ledger_already_existed": batch.ledger_already_existed,
            "final_status": batch.final_status,
            "execution_duration_seconds": batch.execution_duration.total_seconds(),
            "error_type": batch.error_type,
            "error_message": safe_batch_error_message(batch),
        }
    )
    return projection
