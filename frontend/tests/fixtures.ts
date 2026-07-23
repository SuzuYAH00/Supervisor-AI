import type { CommercialEventList } from "../src/features/commercial-events/types/commercial-events";
import type { FinancialSummary } from "../src/features/financial-summary/types/financial-summary";
import type { FinancialTimeline } from "../src/features/financial-timeline/types/financial-timeline";
import type { ProcessingHealth } from "../src/features/processing-health/types/processing-health";
import type { ProcessingRunsResponse } from "../src/features/processing-runs/types/processing-runs";
import type { ProcessingRunDetailResponse } from "../src/features/processing-runs/types/processing-run-detail";

export function processingRunDetail(
  changes: Partial<ProcessingRunDetailResponse> = {},
): ProcessingRunDetailResponse {
  return {
    processing_run: {
      processing_run_id: "run-1",
      event_id: "event-1",
      final_status: "posted",
      started_at: "2026-07-23T14:00:00Z",
      completed_at: "2026-07-23T14:00:01Z",
      rules_engine_version: "rules-1",
      created_at: "2026-07-23T14:00:01Z",
    },
    commercial_event: {
      event_id: "event-1",
      external_reference: "external-1",
      source: "csv-example",
      occurred_at: "2026-07-23T13:59:00Z",
    },
    phases: [
      {
        phase: "contract_facts",
        status: "completed",
        can_continue: true,
      },
      {
        phase: "payment_validation",
        status: "validated",
        can_continue: false,
      },
    ],
    ...changes,
  };
}

export function processingRuns(
  changes: Partial<ProcessingRunsResponse> = {},
): ProcessingRunsResponse {
  return {
    items: [
      {
        processing_run_id: "run-2",
        event_id: "event-2",
        source: "csv-example",
        external_reference: "external-2",
        started_at: "2026-07-23T14:00:00Z",
        completed_at: "2026-07-23T14:00:01Z",
        final_status: "posted",
        rules_engine_version: "rules-1",
      },
    ],
    next_cursor: null,
    ...changes,
  };
}

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

export function financialTimeline(
  changes: Partial<FinancialTimeline> = {},
): FinancialTimeline {
  return {
    collaborator_id: "Employee-A",
    filters: {
      start_date: null,
      end_date: null,
      entry_type: null,
      currency: null,
    },
    page: { limit: 50, next_cursor: null, has_more: false },
    items: [
      {
        ledger_entry_id: "ledger-1",
        posted_at: "2026-07-22T12:05:00Z",
        entry_type: "credit",
        amount: "99.90",
        currency: "BRL",
        invoice_id: null,
        posting_reference: "posting:event-1",
        remuneration_calculation_reference: "calculation:event-1",
        source_reference_ids: ["invoice-1", "ticket-1"],
        commercial_event: {
          event_id: "event-1",
          external_reference: "external-1",
          source: "csv-example",
          occurred_at: "2026-07-22T12:00:00Z",
        },
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
