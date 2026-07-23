import { apiRequest } from "../../../lib/http/api-client";
import {
  booleanValue,
  jsonList,
  jsonObject,
  text,
} from "../../../lib/http/json-contract";
import type {
  ProcessingRunCommercialEvent,
  ProcessingRunDetail,
  ProcessingRunDetailResponse,
  ProcessingRunPhase,
} from "../types/processing-run-detail";

function parseProcessingRun(value: unknown): ProcessingRunDetail {
  const run = jsonObject(value, "processing_run");
  return {
    processing_run_id: text(run.processing_run_id, "processing_run_id"),
    event_id: text(run.event_id, "event_id"),
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

function parseCommercialEvent(value: unknown): ProcessingRunCommercialEvent {
  const event = jsonObject(value, "commercial_event");
  return {
    event_id: text(event.event_id, "commercial_event.event_id"),
    external_reference: text(
      event.external_reference,
      "commercial_event.external_reference",
    ),
    source: text(event.source, "commercial_event.source"),
    occurred_at: text(event.occurred_at, "commercial_event.occurred_at"),
  };
}

function parsePhase(value: unknown): ProcessingRunPhase {
  const phase = jsonObject(value, "phase");
  return {
    phase: text(phase.phase, "phase.phase"),
    status: text(phase.status, "phase.status"),
    can_continue: booleanValue(phase.can_continue, "phase.can_continue"),
  };
}

export function parseProcessingRunDetail(
  value: unknown,
): ProcessingRunDetailResponse {
  const response = jsonObject(value, "processing run detail response");
  return {
    processing_run: parseProcessingRun(response.processing_run),
    commercial_event: parseCommercialEvent(response.commercial_event),
    phases: jsonList(response.phases, parsePhase, "phases"),
  };
}

export function getProcessingRunDetail(
  processingRunId: string,
  signal?: AbortSignal,
): Promise<ProcessingRunDetailResponse> {
  return apiRequest(
    `/processing-runs/${encodeURIComponent(processingRunId)}`,
    { signal, parse: parseProcessingRunDetail },
  );
}
