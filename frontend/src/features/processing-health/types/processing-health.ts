export interface ProcessingHealthFilters {
  readonly start_date: string | null;
  readonly end_date: string | null;
  readonly source: string | null;
  readonly rules_engine_version: string | null;
}

export interface ProcessingRunStatusCount {
  readonly final_status: string;
  readonly count: number;
}

export interface ProcessingRunVersionCount {
  readonly rules_engine_version: string;
  readonly count: number;
}

export interface ProcessingRunHealth {
  readonly total: number;
  readonly by_final_status: readonly ProcessingRunStatusCount[];
  readonly by_rules_engine_version: readonly ProcessingRunVersionCount[];
}

export interface CommercialEventProcessingHealth {
  readonly events_with_processing_runs: number;
  readonly events_without_processing_runs: number;
  readonly events_with_multiple_processing_runs: number;
  readonly events_with_ledger_entries: number;
  readonly events_without_ledger_entries: number;
}

export interface ProcessingHealth {
  readonly filters: ProcessingHealthFilters;
  readonly processing_runs: ProcessingRunHealth;
  readonly commercial_events: CommercialEventProcessingHealth;
}

export interface ProcessingHealthQuery {
  readonly startDate?: string;
  readonly endDate?: string;
  readonly source?: string;
  readonly rulesEngineVersion?: string;
}
