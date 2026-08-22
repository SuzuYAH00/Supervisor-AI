import { apiRequest } from "../../../lib/http/api-client";
import { jsonList, jsonObject, nonNegativeInteger, nullableText, text } from "../../../lib/http/json-contract";
import type { OverrideInput, ScheduleOverride, WorkScheduleFilters, WorkScheduleItem, WorkSchedulesResult } from "../types/work-schedules";

function parseOverride(value: unknown): ScheduleOverride {
  const item = jsonObject(value, "override");
  return { id: text(item.id, "id"), collaborator_id: text(item.collaborator_id, "collaborator_id"), work_date: text(item.work_date, "work_date"), planned_start: text(item.planned_start, "planned_start"), planned_end: text(item.planned_end, "planned_end"), reason: text(item.reason, "reason"), created_by: text(item.created_by, "created_by"), created_at: text(item.created_at, "created_at") };
}

function parseItem(value: unknown): WorkScheduleItem {
  const item = jsonObject(value, "schedule");
  return { collaborator_id: text(item.collaborator_id, "collaborator_id"), display_name: text(item.display_name, "display_name"), work_date: text(item.work_date, "work_date"), planned_start: nullableText(item.planned_start, "planned_start"), planned_end: nullableText(item.planned_end, "planned_end"), resolution_status: text(item.resolution_status, "resolution_status") as WorkScheduleItem["resolution_status"], effective_origin: text(item.effective_origin, "effective_origin"), source: text(item.source, "source"), source_reference: text(item.source_reference, "source_reference"), source_sheet: text(item.source_sheet, "source_sheet"), source_cell: text(item.source_cell, "source_cell"), unresolved_reason: nullableText(item.unresolved_reason, "unresolved_reason"), has_override: item.has_override === true, override: item.override === null ? null : parseOverride(item.override) };
}

export function getWorkSchedules(filters: WorkScheduleFilters, signal?: AbortSignal): Promise<WorkSchedulesResult> {
  const params = new URLSearchParams({ competence_month: filters.competenceMonth });
  if (filters.collaboratorId) params.set("collaborator_id", filters.collaboratorId);
  if (filters.resolutionStatus) params.set("resolution_status", filters.resolutionStatus);
  return apiRequest(`/work-schedules?${params}`, { signal, parse(value) { const root = jsonObject(value, "root"); return { competence_month: text(root.competence_month, "competence_month"), total_count: nonNegativeInteger(root.total_count, "total_count"), pending_count: nonNegativeInteger(root.pending_count, "pending_count"), items: jsonList(root.items, parseItem, "items") }; } });
}

export function createWorkScheduleOverride(input: OverrideInput): Promise<ScheduleOverride> {
  return apiRequest("/work-schedules/overrides", { method: "POST", body: JSON.stringify(input), parse: parseOverride });
}
