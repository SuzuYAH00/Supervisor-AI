import { apiRequest } from "../../../lib/http/api-client";
import {
  jsonList,
  jsonObject,
  nonNegativeInteger,
  nullableText,
  text,
} from "../../../lib/http/json-contract";
import type {
  ProcessingHealth,
  ProcessingHealthQuery,
  ProcessingRunStatusCount,
  ProcessingRunVersionCount,
} from "../types/processing-health";

function statusCount(value: unknown): ProcessingRunStatusCount {
  const item = jsonObject(value, "by_final_status");
  return {
    final_status: text(item.final_status, "final_status"),
    count: nonNegativeInteger(item.count, "count"),
  };
}

function versionCount(value: unknown): ProcessingRunVersionCount {
  const item = jsonObject(value, "by_rules_engine_version");
  return {
    rules_engine_version: text(
      item.rules_engine_version,
      "rules_engine_version",
    ),
    count: nonNegativeInteger(item.count, "count"),
  };
}

export function parseProcessingHealth(value: unknown): ProcessingHealth {
  const root = jsonObject(value, "root");
  const filters = jsonObject(root.filters, "filters");
  const runs = jsonObject(root.processing_runs, "processing_runs");
  const events = jsonObject(root.commercial_events, "commercial_events");

  return {
    filters: {
      start_date: nullableText(filters.start_date, "start_date"),
      end_date: nullableText(filters.end_date, "end_date"),
      source: nullableText(filters.source, "source"),
      rules_engine_version: nullableText(
        filters.rules_engine_version,
        "rules_engine_version",
      ),
    },
    processing_runs: {
      total: nonNegativeInteger(runs.total, "total"),
      by_final_status: jsonList(
        runs.by_final_status,
        statusCount,
        "by_final_status",
      ),
      by_rules_engine_version: jsonList(
        runs.by_rules_engine_version,
        versionCount,
        "by_rules_engine_version",
      ),
    },
    commercial_events: {
      events_with_processing_runs: nonNegativeInteger(
        events.events_with_processing_runs,
        "events_with_processing_runs",
      ),
      events_without_processing_runs: nonNegativeInteger(
        events.events_without_processing_runs,
        "events_without_processing_runs",
      ),
      events_with_multiple_processing_runs: nonNegativeInteger(
        events.events_with_multiple_processing_runs,
        "events_with_multiple_processing_runs",
      ),
      events_with_ledger_entries: nonNegativeInteger(
        events.events_with_ledger_entries,
        "events_with_ledger_entries",
      ),
      events_without_ledger_entries: nonNegativeInteger(
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
