import { apiRequest } from "../../../lib/http/api-client";
import {
  parseProcessingRuns,
  type ProcessingRunsQuery,
  type ProcessingRunsResponse,
} from "../types/processing-runs";

function buildSearchParams(query: ProcessingRunsQuery): URLSearchParams {
  const searchParams = new URLSearchParams();

  if (query.source !== undefined) searchParams.set("source", query.source);
  if (query.externalReference !== undefined) {
    searchParams.set("external_reference", query.externalReference);
  }
  if (query.finalStatus !== undefined) {
    searchParams.set("final_status", query.finalStatus);
  }
  if (query.rulesEngineVersion !== undefined) {
    searchParams.set("rules_engine_version", query.rulesEngineVersion);
  }
  if (query.startDate !== undefined) {
    searchParams.set("start_date", query.startDate);
  }
  if (query.endDate !== undefined) searchParams.set("end_date", query.endDate);
  if (query.limit !== undefined) {
    searchParams.set("limit", query.limit.toString());
  }
  if (query.cursor !== undefined) searchParams.set("cursor", query.cursor);

  return searchParams;
}

export async function getProcessingRuns(
  query: ProcessingRunsQuery = {},
  signal?: AbortSignal,
): Promise<ProcessingRunsResponse> {
  const searchParams = buildSearchParams(query);
  const queryString = searchParams.toString();
  const path = `/processing-runs${queryString === "" ? "" : `?${queryString}`}`;
  return apiRequest(path, { signal, parse: parseProcessingRuns });
}
