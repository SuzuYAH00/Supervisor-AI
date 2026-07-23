import json
from pathlib import Path

from supervisor_ai.infrastructure.importing import CsvBatchImportResult
from supervisor_ai.infrastructure.importing.reporting import (
    CorrelatedCsvRowResult,
    correlate_csv_rows,
    has_csv_import_failures,
    project_csv_import_report,
    safe_batch_error_message,
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
        lines.extend(_format_text_row(item) for item in correlate_csv_rows(result))
    return "\n".join(lines) + "\n"


def format_json_report(file_path: Path, result: CsvBatchImportResult) -> str:
    projection = project_csv_import_report(file_path.name, result)
    return json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def has_failures(result: CsvBatchImportResult) -> bool:
    return has_csv_import_failures(result)


def _format_text_row(item: CorrelatedCsvRowResult) -> str:
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
        message = safe_batch_error_message(batch)
        return (
            f"Linha {row.line_number} | {identifier} | "
            f"{batch.processing_status.value.upper()} | {batch.error_type} | "
            f"{message}"
        )
    return (
        f"Linha {row.line_number} | {identifier} | "
        f"{batch.processing_status.value.upper()}"
    )
