import { apiRequest } from "../../../lib/http/api-client";
import {
  booleanValue,
  jsonList,
  jsonObject,
  nonNegativeInteger,
  nullableText,
  text,
} from "../../../lib/http/json-contract";
import type {
  FinancialTimeline,
  FinancialTimelineItem,
  FinancialTimelineQuery,
  TimelineCommercialEvent,
} from "../types/financial-timeline";

function commercialEvent(value: unknown): TimelineCommercialEvent {
  const item = jsonObject(value, "commercial_event");
  return {
    event_id: text(item.event_id, "event_id"),
    external_reference: text(
      item.external_reference,
      "external_reference",
    ),
    source: text(item.source, "source"),
    occurred_at: text(item.occurred_at, "occurred_at"),
  };
}

function timelineItem(value: unknown): FinancialTimelineItem {
  const item = jsonObject(value, "items");
  return {
    ledger_entry_id: text(item.ledger_entry_id, "ledger_entry_id"),
    posted_at: text(item.posted_at, "posted_at"),
    entry_type: text(item.entry_type, "entry_type"),
    amount: text(item.amount, "amount"),
    currency: text(item.currency, "currency"),
    invoice_id: nullableText(item.invoice_id, "invoice_id"),
    posting_reference: text(item.posting_reference, "posting_reference"),
    remuneration_calculation_reference: text(
      item.remuneration_calculation_reference,
      "remuneration_calculation_reference",
    ),
    source_reference_ids: jsonList(
      item.source_reference_ids,
      (reference) => text(reference, "source_reference_ids"),
      "source_reference_ids",
    ),
    commercial_event: commercialEvent(item.commercial_event),
  };
}

export function parseFinancialTimeline(value: unknown): FinancialTimeline {
  const root = jsonObject(value, "root");
  const filters = jsonObject(root.filters, "filters");
  const page = jsonObject(root.page, "page");
  const nextCursor = nullableText(page.next_cursor, "next_cursor");
  const hasMore = booleanValue(page.has_more, "has_more");
  if (
    (hasMore && nextCursor === null) ||
    (!hasMore && nextCursor !== null)
  ) {
    throw new TypeError(
      "Invalid pagination: has_more and next_cursor are inconsistent",
    );
  }
  return {
    collaborator_id: text(root.collaborator_id, "collaborator_id"),
    filters: {
      start_date: nullableText(filters.start_date, "start_date"),
      end_date: nullableText(filters.end_date, "end_date"),
      entry_type: nullableText(filters.entry_type, "entry_type"),
      currency: nullableText(filters.currency, "currency"),
    },
    page: {
      limit: nonNegativeInteger(page.limit, "limit"),
      next_cursor: nextCursor,
      has_more: hasMore,
    },
    items: jsonList(root.items, timelineItem, "items"),
  };
}

export function getFinancialTimeline(
  collaboratorId: string,
  query: FinancialTimelineQuery = {},
  signal?: AbortSignal,
): Promise<FinancialTimeline> {
  const parameters = new URLSearchParams();
  if (query.startDate !== undefined) {
    parameters.set("start_date", query.startDate);
  }
  if (query.endDate !== undefined) {
    parameters.set("end_date", query.endDate);
  }
  if (query.entryType !== undefined) {
    parameters.set("entry_type", query.entryType);
  }
  if (query.currency !== undefined) {
    parameters.set("currency", query.currency);
  }
  if (query.limit !== undefined) {
    parameters.set("limit", String(query.limit));
  }
  if (query.cursor !== undefined) {
    parameters.set("cursor", query.cursor);
  }
  const serialized = parameters.toString();
  const path = `/collaborators/${encodeURIComponent(collaboratorId)}/financial-timeline`;
  return apiRequest(serialized === "" ? path : `${path}?${serialized}`, {
    signal,
    parse: parseFinancialTimeline,
  });
}
