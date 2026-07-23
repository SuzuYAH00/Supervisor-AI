import { apiRequest } from "../../../lib/http/api-client";
import type {
  ProcessingHealth,
  ProcessingHealthQuery,
  ProcessingRunStatusCount,
  ProcessingRunVersionCount,
} from "../types/processing-health";

type JsonObject = { readonly [key: string]: unknown };

function object(value: unknown, field: string): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new TypeError(`Invalid ${field}`);
  }
  const result: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value)) {
    result[key] = item;
  }
  return result;
}

function textOrNull(value: unknown, field: string): string | null {
  if (value === null || typeof value === "string") {
    return value;
  }
  throw new TypeError(`Invalid ${field}`);
}

function count(value: unknown, field: string): number {
  if (typeof value === "number" && Number.isInteger(value) && value >= 0) {
    return value;
  }
  throw new TypeError(`Invalid ${field}`);
}

function list<T>(
  value: unknown,
  parseItem: (item: unknown) => T,
  field: string,
): readonly T[] {
  if (!Array.isArray(value)) {
    throw new TypeError(`Invalid ${field}`);
  }
  return value.map(parseItem);
}

function statusCount(value: unknown): ProcessingRunStatusCount {
  const item = object(value, "by_final_status");
  if (typeof item.final_status !== "string") {
    throw new TypeError("Invalid final_status");
  }
  return {
    final_status: item.final_status,
    count: count(item.count, "count"),
  };
}

function versionCount(value: unknown): ProcessingRunVersionCount {
  const item = object(value, "by_rules_engine_version");
  if (typeof item.rules_engine_version !== "string") {
    throw new TypeError("Invalid rules_engine_version");
  }
  return {
    rules_engine_version: item.rules_engine_version,
    count: count(item.count, "count"),
  };
}

export function parseProcessingHealth(value: unknown): ProcessingHealth {
  const root = object(value, "root");
  const filters = object(root.filters, "filters");
  const runs = object(root.processing_runs, "processing_runs");
  const events = object(root.commercial_events, "commercial_events");

  return {
    filters: {
      start_date: textOrNull(filters.start_date, "start_date"),
      end_date: textOrNull(filters.end_date, "end_date"),
      source: textOrNull(filters.source, "source"),
      rules_engine_version: textOrNull(
        filters.rules_engine_version,
        "rules_engine_version",
      ),
    },
    processing_runs: {
      total: count(runs.total, "total"),
      by_final_status: list(
        runs.by_final_status,
        statusCount,
        "by_final_status",
      ),
      by_rules_engine_version: list(
        runs.by_rules_engine_version,
        versionCount,
        "by_rules_engine_version",
      ),
    },
    commercial_events: {
      events_with_processing_runs: count(
        events.events_with_processing_runs,
        "events_with_processing_runs",
      ),
      events_without_processing_runs: count(
        events.events_without_processing_runs,
        "events_without_processing_runs",
      ),
      events_with_multiple_processing_runs: count(
        events.events_with_multiple_processing_runs,
        "events_with_multiple_processing_runs",
      ),
      events_with_ledger_entries: count(
        events.events_with_ledger_entries,
        "events_with_ledger_entries",
      ),
      events_without_ledger_entries: count(
        events.events_without_ledger_entries,
        "events_without_ledger_entries",
      ),
    },
  };
}

export function getProcessingHealth(
  filters: ProcessingHealthQuery = {},
  signal?: AbortSignal,
): Promise<ProcessingHealth> {
  const parameters = new URLSearchParams();
  if (filters.startDate !== undefined) {
    parameters.set("start_date", filters.startDate);
  }
  if (filters.endDate !== undefined) {
    parameters.set("end_date", filters.endDate);
  }
  if (filters.source !== undefined) {
    parameters.set("source", filters.source);
  }
  if (filters.rulesEngineVersion !== undefined) {
    parameters.set("rules_engine_version", filters.rulesEngineVersion);
  }
  const query = parameters.toString();
  const path = query === "" ? "/processing/health" : `/processing/health?${query}`;
  return apiRequest(path, { signal, parse: parseProcessingHealth });
}
