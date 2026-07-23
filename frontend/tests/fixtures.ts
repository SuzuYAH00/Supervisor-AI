import type { CommercialEventList } from "../src/features/commercial-events/types/commercial-events";
import type { FinancialSummary } from "../src/features/financial-summary/types/financial-summary";
import type { ProcessingHealth } from "../src/features/processing-health/types/processing-health";

export function commercialEvents(
  changes: Partial<CommercialEventList> = {},
): CommercialEventList {
  return {
    filters: {
      source: null,
      external_reference: null,
      start_date: null,
      end_date: null,
    },
    page: {
      limit: 50,
      next_cursor: null,
      has_more: false,
    },
    items: [
      {
        event_id: "event-2",
        external_reference: "external-2",
        source: "csv-example",
        occurred_at: "2026-07-22T12:00:00Z",
        received_at: "2026-07-22T12:01:00Z",
        created_at: "2026-07-22T12:01:00Z",
      },
    ],
    ...changes,
  };
}

export function financialSummary(
  changes: Partial<FinancialSummary> = {},
): FinancialSummary {
  return {
    filters: { collaborator_id: null, start_date: null, end_date: null },
    collaborator_count: 2,
    credit_count: 3,
    totals_by_currency: [
      { currency: "BRL", amount: "219.80" },
      { currency: "USD", amount: "10.00" },
    ],
    collaborators: [
      {
        collaborator_id: "employee-2",
        credit_count: 1,
        totals_by_currency: [
          {
            currency: "USD",
            amount: "10.00",
            credit_count: 1,
            rank: 9,
            share_percentage: "12.50",
          },
        ],
      },
      {
        collaborator_id: "employee-1",
        credit_count: 2,
        totals_by_currency: [
          {
            currency: "BRL",
            amount: "219.80",
            credit_count: 2,
            rank: 4,
            share_percentage: "37.25",
          },
        ],
      },
    ],
    ...changes,
  };
}

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
