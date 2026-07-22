import json
from dataclasses import dataclass
from pathlib import Path

from supervisor_ai.infrastructure.importing import (
    BatchDocumentResult,
    BatchDocumentStatus,
    CsvBatchImportResult,
    CsvRowResult,
)


@dataclass(frozen=True, slots=True)
class CorrelatedRowResult:
    csv_row: CsvRowResult
    batch_result: BatchDocumentResult | None


def correlate_rows(result: CsvBatchImportResult) -> tuple[CorrelatedRowResult, ...]:
    by_identifier = {
        item.document_identifier: item for item in result.batch.ordered_results
    }
    return tuple(
        CorrelatedRowResult(
            csv_row=row,
            batch_result=(
                None
                if row.document_identifier is None
                else by_identifier.get(row.document_identifier)
            ),
        )
        for row in result.parsing.rows
    )


def format_text_report(
    file_path: Path,
    result: CsvBatchImportResult,
    *,
    verbose: bool,
) -> str:
    parsing = result.parsing.statistics
    processing = result.batch.statistics
    lines = [
        "Importação CSV concluída",
        "",
        f"Arquivo: {file_path.name}",
        "",
        "Parsing:",
        f"- linhas de dados: {parsing.total_data_rows}",
        f"- linhas convertidas: {parsing.converted_rows}",
        f"- linhas inválidas: {parsing.error_rows}",
        f"- linhas vazias ignoradas: {parsing.ignored_empty_rows}",
        "",
        "Processamento:",
        f"- documentos processados: {processing.total_documents}",
        f"- sucessos: {processing.successful_documents}",
        f"- conflitos de negócio: {processing.business_conflicts}",
        f"- erros de validação: {processing.validation_errors}",
        f"- falhas técnicas: {processing.technical_errors}",
        f"- ProcessingRuns criados: {processing.processing_runs_created}",
        f"- LedgerEntries criadas: {processing.ledger_entries_created}",
        f"- duração total: {result.batch.processing_duration.total_seconds():.2f}s",
    ]
    if verbose:
        lines.extend(("", "Resultados por linha:"))
        lines.extend(_format_text_row(item) for item in correlate_rows(result))
    return "\n".join(lines) + "\n"


def format_json_report(file_path: Path, result: CsvBatchImportResult) -> str:
    parsing = result.parsing.statistics
    processing = result.batch.statistics
    failed = (
        parsing.error_rows
        + processing.validation_errors
        + processing.business_conflicts
        + processing.technical_errors
    )
    projection: dict[str, object] = {
        "file": file_path.name,
        "status": "success" if failed == 0 else "partial_failure",
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
        "results": [_json_row(item) for item in correlate_rows(result)],
    }
    return json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def has_failures(result: CsvBatchImportResult) -> bool:
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


def _format_text_row(item: CorrelatedRowResult) -> str:
    row = item.csv_row
    identifier = row.document_identifier or "-"
    if row.errors:
        error = row.errors[0]
        return (
            f"Linha {row.line_number} | {identifier} | CSV_ROW_ERROR | "
            f"{error.column} | {error.message}"
        )
    batch = item.batch_result
    if batch is None:
        return (
            f"Linha {row.line_number} | {identifier} | "
            "TECHNICAL_ERROR | missing result"
        )
    if batch.error_type is not None:
        message = _safe_batch_error_message(batch)
        return (
            f"Linha {row.line_number} | {identifier} | "
            f"{batch.processing_status.value.upper()} | {batch.error_type} | "
            f"{message}"
        )
    return (
        f"Linha {row.line_number} | {identifier} | "
        f"{batch.processing_status.value.upper()}"
    )


def _json_row(item: CorrelatedRowResult) -> dict[str, object]:
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
            "error_message": _safe_batch_error_message(batch),
        }
    )
    return projection


def _safe_batch_error_message(result: BatchDocumentResult) -> str | None:
    if result.processing_status is BatchDocumentStatus.TECHNICAL_ERROR:
        return "technical processing failure"
    return result.error_message
