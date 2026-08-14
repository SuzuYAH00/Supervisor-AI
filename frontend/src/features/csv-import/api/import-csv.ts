import { apiRequest } from "../../../lib/http/api-client";
import {
  jsonList,
  jsonObject,
  nonNegativeInteger,
  nullableText,
  text,
} from "../../../lib/http/json-contract";
import type {
  CsvImportProcessing,
  CsvImportResult,
  CsvImportRow,
} from "../types/csv-import";

function nonNegativeNumber(value: unknown, field: string): number {
  if (typeof value === "number" && Number.isFinite(value) && value >= 0) {
    return value;
  }
  throw new TypeError(`Invalid ${field}`);
}

function nullableBoolean(value: unknown, field: string): boolean | null {
  if (value === null || typeof value === "boolean") return value;
  throw new TypeError(`Invalid ${field}`);
}

function nullableNumber(value: unknown, field: string): number | null {
  if (value === null) return null;
  return nonNegativeNumber(value, field);
}

function parseStatus(value: unknown): CsvImportResult["status"] {
  if (value === "success" || value === "partial_failure") return value;
  throw new TypeError("Invalid status");
}

function parseProcessing(value: unknown): CsvImportProcessing {
  const processing = jsonObject(value, "processing");
  return {
    total_documents: nonNegativeInteger(
      processing.total_documents,
      "total_documents",
    ),
    successful_documents: nonNegativeInteger(
      processing.successful_documents,
      "successful_documents",
    ),
    validation_errors: nonNegativeInteger(
      processing.validation_errors,
      "validation_errors",
    ),
    business_conflicts: nonNegativeInteger(
      processing.business_conflicts,
      "business_conflicts",
    ),
    technical_errors: nonNegativeInteger(
      processing.technical_errors,
      "technical_errors",
    ),
    processing_runs_created: nonNegativeInteger(
      processing.processing_runs_created,
      "processing_runs_created",
    ),
    ledger_entries_created: nonNegativeInteger(
      processing.ledger_entries_created,
      "ledger_entries_created",
    ),
  };
}

function parseRow(value: unknown): CsvImportRow {
  const row = jsonObject(value, "result");
  return {
    line_number: nonNegativeInteger(row.line_number, "line_number"),
    document_identifier: nullableText(
      row.document_identifier,
      "document_identifier",
    ),
    status: text(row.status, "result.status"),
    column: nullableText(row.column, "column"),
    commercial_event_id: nullableText(
      row.commercial_event_id,
      "commercial_event_id",
    ),
    processing_run_id: nullableText(
      row.processing_run_id,
      "processing_run_id",
    ),
    ledger_entry_id: nullableText(row.ledger_entry_id, "ledger_entry_id"),
    event_persisted: nullableBoolean(row.event_persisted, "event_persisted"),
    ledger_persisted: nullableBoolean(row.ledger_persisted, "ledger_persisted"),
    ledger_already_existed: nullableBoolean(
      row.ledger_already_existed,
      "ledger_already_existed",
    ),
    final_status: nullableText(row.final_status, "final_status"),
    execution_duration_seconds: nullableNumber(
      row.execution_duration_seconds,
      "execution_duration_seconds",
    ),
    error_type: nullableText(row.error_type, "error_type"),
    error_message: nullableText(row.error_message, "error_message"),
  };
}

export function parseCsvImportResult(value: unknown): CsvImportResult {
  const result = jsonObject(value, "CSV import result");
  const parsing = jsonObject(result.parsing, "parsing");
  return {
    file: text(result.file, "file"),
    status: parseStatus(result.status),
    parsing: {
      total_data_rows: nonNegativeInteger(
        parsing.total_data_rows,
        "total_data_rows",
      ),
      converted_rows: nonNegativeInteger(
        parsing.converted_rows,
        "converted_rows",
      ),
      error_rows: nonNegativeInteger(parsing.error_rows, "error_rows"),
      ignored_empty_rows: nonNegativeInteger(
        parsing.ignored_empty_rows,
        "ignored_empty_rows",
      ),
    },
    processing: parseProcessing(result.processing),
    duration_seconds: nonNegativeNumber(
      result.duration_seconds,
      "duration_seconds",
    ),
    started_at: text(result.started_at, "started_at"),
    completed_at: text(result.completed_at, "completed_at"),
    results: jsonList(result.results, parseRow, "results"),
  };
}

export function importCsv(
  file: File,
  signal?: AbortSignal,
): Promise<CsvImportResult> {
  const formData = new FormData();
  formData.set("file", file);
  return apiRequest("/imports/csv", {
    method: "POST",
    body: formData,
    signal,
    parse: parseCsvImportResult,
  });
}
