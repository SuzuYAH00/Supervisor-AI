export const csvImportResult = {
  file: "events.csv",
  status: "success",
  parsing: { total_data_rows: 1, converted_rows: 1, error_rows: 0, ignored_empty_rows: 0 },
  processing: {
    total_documents: 1, successful_documents: 1, validation_errors: 0,
    business_conflicts: 0, technical_errors: 0, processing_runs_created: 1,
    ledger_entries_created: 1,
  },
  duration_seconds: 0.25,
  started_at: "2026-07-23T12:00:00Z",
  completed_at: "2026-07-23T12:00:01Z",
  results: [{
    line_number: 2, document_identifier: "document-1", status: "processed",
    column: null, commercial_event_id: "event-1", processing_run_id: "run/1",
    ledger_entry_id: "ledger-1", event_persisted: true, ledger_persisted: true,
    ledger_already_existed: false, final_status: "posted",
    execution_duration_seconds: 0.1, error_type: null, error_message: null,
  }],
} as const;
