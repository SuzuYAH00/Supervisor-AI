import {
  jsonList,
  jsonObject,
  nullableText,
  text,
} from "../../../lib/http/json-contract";

export interface ProcessingRunListItem {
  readonly processing_run_id: string;
  readonly event_id: string;
  readonly source: string;
  readonly external_reference: string;
  readonly started_at: string;
  readonly completed_at: string;
  readonly final_status: string;
  readonly rules_engine_version: string;
}

export interface ProcessingRunsResponse {
  readonly items: readonly ProcessingRunListItem[];
  readonly next_cursor: string | null;
}

export interface ProcessingRunsQuery {
  source?: string;
  externalReference?: string;
  finalStatus?: string;
  rulesEngineVersion?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  cursor?: string;
}

function parseProcessingRunItem(value: unknown): ProcessingRunListItem {
  const item = jsonObject(value, "processing run item");

  return {
    processing_run_id: text(item.processing_run_id, "processing_run_id"),
    event_id: text(item.event_id, "event_id"),
    source: text(item.source, "source"),
    external_reference: text(item.external_reference, "external_reference"),
    started_at: text(item.started_at, "started_at"),
    completed_at: text(item.completed_at, "completed_at"),
    final_status: text(item.final_status, "final_status"),
    rules_engine_version: text(
      item.rules_engine_version,
      "rules_engine_version",
    ),
  };
}

export function parseProcessingRuns(value: unknown): ProcessingRunsResponse {
  const response = jsonObject(value, "processing runs response");

  return {
    items: jsonList(response.items, parseProcessingRunItem, "items"),
    next_cursor: nullableText(response.next_cursor, "next_cursor"),
  };
}
