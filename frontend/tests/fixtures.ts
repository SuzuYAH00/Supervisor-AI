import type { ProcessingHealth } from "../src/features/processing-health/types/processing-health";

export function processingHealth(
  changes: Partial<ProcessingHealth> = {},
): ProcessingHealth {
  return {
    filters: {
      start_date: null,
      end_date: null,
      source: null,
      rules_engine_version: null,
    },
    processing_runs: {
      total: 3,
      by_final_status: [
        { final_status: "posted", count: 2 },
        { final_status: "not_evaluable", count: 1 },
      ],
      by_rules_engine_version: [
        { rules_engine_version: "rules-2", count: 1 },
        { rules_engine_version: "rules-1", count: 2 },
      ],
    },
    commercial_events: {
      events_with_processing_runs: 2,
      events_without_processing_runs: 1,
      events_with_multiple_processing_runs: 1,
      events_with_ledger_entries: 2,
      events_without_ledger_entries: 1,
    },
    ...changes,
  };
}
