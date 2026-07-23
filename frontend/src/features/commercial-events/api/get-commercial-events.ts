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
  CommercialEventList,
  CommercialEventListItem,
  CommercialEventsQuery,
} from "../types/commercial-events";

function commercialEvent(value: unknown): CommercialEventListItem {
  const item = jsonObject(value, "items");
  return {
    event_id: text(item.event_id, "event_id"),
    external_reference: text(
      item.external_reference,
      "external_reference",
    ),
    source: text(item.source, "source"),
    occurred_at: text(item.occurred_at, "occurred_at"),
    received_at: text(item.received_at, "received_at"),
    created_at: text(item.created_at, "created_at"),
  };
}

export function parseCommercialEvents(value: unknown): CommercialEventList {
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
    filters: {
      source: nullableText(filters.source, "source"),
      external_reference: nullableText(
        filters.external_reference,
        "external_reference",
      ),
      start_date: nullableText(filters.start_date, "start_date"),
      end_date: nullableText(filters.end_date, "end_date"),
    },
    page: {
      limit: nonNegativeInteger(page.limit, "limit"),
      next_cursor: nextCursor,
      has_more: hasMore,
    },
    items: jsonList(root.items, commercialEvent, "items"),
  };
}

export function getCommercialEvents(
  query: CommercialEventsQuery = {},
  signal?: AbortSignal,
): Promise<CommercialEventList> {
  const parameters = new URLSearchParams();
  if (query.source !== undefined) {
    parameters.set("source", query.source);
  }
  if (query.externalReference !== undefined) {
    parameters.set("external_reference", query.externalReference);
  }
  if (query.startDate !== undefined) {
    parameters.set("start_date", query.startDate);
  }
  if (query.endDate !== undefined) {
    parameters.set("end_date", query.endDate);
  }
  if (query.limit !== undefined) {
    parameters.set("limit", String(query.limit));
  }
  if (query.cursor !== undefined) {
    parameters.set("cursor", query.cursor);
  }
  const serialized = parameters.toString();
  const path =
    serialized === "" ? "/commercial-events" : `/commercial-events?${serialized}`;
  return apiRequest(path, { signal, parse: parseCommercialEvents });
}
