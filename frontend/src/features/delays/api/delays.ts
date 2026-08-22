import { apiRequest } from "../../../lib/http/api-client";
import { booleanValue, jsonList, jsonObject, nonNegativeInteger, nullableText, text } from "../../../lib/http/json-contract";
import type { DelayReview, OperationalDelay, OperationalDelaysResult } from "../types/delays";

function review(value: unknown): DelayReview {
  const item = jsonObject(value, "review");
  return { id: text(item.id, "id"), decision: text(item.decision, "decision") as DelayReview["decision"], decided_at: text(item.decided_at, "decided_at"), decided_by: text(item.decided_by, "decided_by"), employee_occurrence_report_id: nullableText(item.employee_occurrence_report_id, "employee_occurrence_report_id"), note: nullableText(item.note, "note") };
}

function delay(value: unknown): OperationalDelay {
  const item = jsonObject(value, "delay");
  const source = jsonObject(item.source_fact, "source_fact");
  const schedule = item.schedule === null ? null : jsonObject(item.schedule, "schedule");
  return {
    delay_occurrence_id: text(item.delay_occurrence_id, "delay_occurrence_id"), collaborator_id: text(item.collaborator_id, "collaborator_id"), display_name: text(item.display_name, "display_name"), occurrence_date: text(item.occurrence_date, "occurrence_date"), occurrence_type: text(item.occurrence_type, "occurrence_type") as OperationalDelay["occurrence_type"], review_status: text(item.review_status, "review_status") as OperationalDelay["review_status"], counts_for_rv: booleanValue(item.counts_for_rv, "counts_for_rv"), observed_seconds: nonNegativeInteger(item.observed_seconds, "observed_seconds"), applied_limit_seconds: nonNegativeInteger(item.applied_limit_seconds, "applied_limit_seconds"),
    source_fact: { queue: text(source.queue, "queue"), started_at: text(source.started_at, "started_at"), ended_at: text(source.ended_at, "ended_at"), duration_seconds: nonNegativeInteger(source.duration_seconds, "duration_seconds"), pause_type: nullableText(source.pause_type, "pause_type") },
    schedule: schedule === null ? null : { planned_start: text(schedule.planned_start, "planned_start"), planned_end: nullableText(schedule.planned_end, "planned_end"), effective_origin: text(schedule.effective_origin, "effective_origin") },
    review: item.review === null ? null : review(item.review),
    possible_employee_occurrence_reports: jsonList(item.possible_employee_occurrence_reports, (entry) => { const report = jsonObject(entry, "report"); return { id: text(report.id, "id"), external_reference: text(report.external_reference, "external_reference"), external_collaborator_identity: text(report.external_collaborator_identity, "external_collaborator_identity"), submitted_at: text(report.submitted_at, "submitted_at"), occurrence_date: text(report.occurrence_date, "occurrence_date"), reason_text: text(report.reason_text, "reason_text") }; }, "possible_employee_occurrence_reports"),
  };
}

export function getOperationalDelays(filters: { competenceMonth: string; collaboratorId?: string; delayType?: string; reviewStatus?: string }, signal?: AbortSignal): Promise<OperationalDelaysResult> {
  const parameters = new URLSearchParams({ competence_month: filters.competenceMonth });
  if (filters.collaboratorId) parameters.set("collaborator_id", filters.collaboratorId);
  if (filters.delayType) parameters.set("delay_type", filters.delayType);
  if (filters.reviewStatus) parameters.set("review_status", filters.reviewStatus);
  return apiRequest(`/delays?${parameters}`, { signal, parse(value) { const root = jsonObject(value, "root"); return { competence_month: text(root.competence_month, "competence_month"), detected_count: nonNegativeInteger(root.detected_count, "detected_count"), pending_count: nonNegativeInteger(root.pending_count, "pending_count"), valid_count: nonNegativeInteger(root.valid_count, "valid_count"), corrected_count: nonNegativeInteger(root.corrected_count, "corrected_count"), items: jsonList(root.items, delay, "items") }; } });
}

export function createDelayReview(delayId: string, input: { decision: "valid" | "corrected"; employee_occurrence_report_id?: string; note?: string }): Promise<DelayReview> {
  return apiRequest(`/delays/${encodeURIComponent(delayId)}/reviews`, { method: "POST", body: JSON.stringify(input), parse: review });
}
