export interface CommercialEventDetail {
  readonly event_id: string;
  readonly external_reference: string;
  readonly source: string;
  readonly occurred_at: string;
  readonly received_at: string;
  readonly created_at: string;
}

export interface CommercialEventLedgerEntry {
  readonly ledger_entry_id: string;
  readonly event_id: string;
  readonly beneficiary_id: string;
  readonly entry_type: string;
  readonly amount: string;
  readonly currency: string;
  readonly posted_at: string;
  readonly posting_reference: string;
  readonly remuneration_calculation_reference: string;
  readonly invoice_id: string | null;
  readonly source_reference_ids: readonly string[];
}

export interface CommercialEventProcessingRun {
  readonly processing_run_id: string;
  readonly event_id: string;
  readonly final_status: string;
  readonly started_at: string;
  readonly completed_at: string;
  readonly rules_engine_version: string;
  readonly created_at: string;
}

export interface CommercialEventDetailResponse {
  readonly commercial_event: CommercialEventDetail;
  readonly ledger_entries: readonly CommercialEventLedgerEntry[];
  readonly processing_runs: readonly CommercialEventProcessingRun[];
}
