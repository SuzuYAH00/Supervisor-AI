export interface CsvImportParsing {
  readonly total_data_rows: number;
  readonly converted_rows: number;
  readonly error_rows: number;
  readonly ignored_empty_rows: number;
}

export interface CsvImportProcessing {
  readonly total_documents: number;
  readonly successful_documents: number;
  readonly validation_errors: number;
  readonly business_conflicts: number;
  readonly technical_errors: number;
  readonly processing_runs_created: number;
  readonly ledger_entries_created: number;
}

export interface CsvImportRow {
  readonly line_number: number;
  readonly document_identifier: string | null;
  readonly status: string;
  readonly column: string | null;
  readonly commercial_event_id: string | null;
  readonly processing_run_id: string | null;
  readonly ledger_entry_id: string | null;
  readonly event_persisted: boolean | null;
  readonly ledger_persisted: boolean | null;
  readonly ledger_already_existed: boolean | null;
  readonly final_status: string | null;
  readonly execution_duration_seconds: number | null;
  readonly error_type: string | null;
  readonly error_message: string | null;
}

export interface CsvImportResult {
  readonly file: string;
  readonly status: "success" | "partial_failure";
  readonly parsing: CsvImportParsing;
  readonly processing: CsvImportProcessing;
  readonly duration_seconds: number;
  readonly started_at: string;
  readonly completed_at: string;
  readonly results: readonly CsvImportRow[];
}
