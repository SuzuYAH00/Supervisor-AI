import { apiRequest } from "../../../lib/http/api-client";
import {
  jsonList,
  jsonObject,
  nullableText,
  text,
} from "../../../lib/http/json-contract";
import type {
  CommercialEventDetail,
  CommercialEventDetailResponse,
  CommercialEventLedgerEntry,
  CommercialEventProcessingRun,
} from "../types/commercial-event-detail";

function parseEvent(value: unknown): CommercialEventDetail {
  const event = jsonObject(value, "commercial_event");
  return {
    event_id: text(event.event_id, "commercial_event.event_id"),
    external_reference: text(
      event.external_reference,
      "commercial_event.external_reference",
    ),
    source: text(event.source, "commercial_event.source"),
    occurred_at: text(event.occurred_at, "commercial_event.occurred_at"),
    received_at: text(event.received_at, "commercial_event.received_at"),
    created_at: text(event.created_at, "commercial_event.created_at"),
  };
}

function parseLedgerEntry(value: unknown): CommercialEventLedgerEntry {
  const entry = jsonObject(value, "ledger_entry");
  return {
    ledger_entry_id: text(entry.ledger_entry_id, "ledger_entry_id"),
    event_id: text(entry.event_id, "ledger_entry.event_id"),
    beneficiary_id: text(entry.beneficiary_id, "beneficiary_id"),
    entry_type: text(entry.entry_type, "entry_type"),
    amount: text(entry.amount, "amount"),
    currency: text(entry.currency, "currency"),
    posted_at: text(entry.posted_at, "posted_at"),
    posting_reference: text(entry.posting_reference, "posting_reference"),
    remuneration_calculation_reference: text(
      entry.remuneration_calculation_reference,
      "remuneration_calculation_reference",
    ),
    invoice_id: nullableText(entry.invoice_id, "invoice_id"),
    source_reference_ids: jsonList(
      entry.source_reference_ids,
      (item) => text(item, "source_reference_id"),
      "source_reference_ids",
    ),
  };
}

function parseProcessingRun(value: unknown): CommercialEventProcessingRun {
  const run = jsonObject(value, "processing_run");
  return {
    processing_run_id: text(run.processing_run_id, "processing_run_id"),
    event_id: text(run.event_id, "processing_run.event_id"),
    final_status: text(run.final_status, "final_status"),
    started_at: text(run.started_at, "started_at"),
    completed_at: text(run.completed_at, "completed_at"),
    rules_engine_version: text(
      run.rules_engine_version,
      "rules_engine_version",
    ),
    created_at: text(run.created_at, "created_at"),
  };
}

export function parseCommercialEventDetail(
  value: unknown,
): CommercialEventDetailResponse {
  const response = jsonObject(value, "commercial event detail response");
  return {
    commercial_event: parseEvent(response.commercial_event),
    ledger_entries: jsonList(
      response.ledger_entries,
      parseLedgerEntry,
      "ledger_entries",
    ),
    processing_runs: jsonList(
      response.processing_runs,
      parseProcessingRun,
      "processing_runs",
    ),
  };
}

export function getCommercialEventDetail(
  eventId: string,
  signal?: AbortSignal,
): Promise<CommercialEventDetailResponse> {
  return apiRequest(`/commercial-events/${encodeURIComponent(eventId)}`, {
    signal,
    parse: parseCommercialEventDetail,
  });
}
