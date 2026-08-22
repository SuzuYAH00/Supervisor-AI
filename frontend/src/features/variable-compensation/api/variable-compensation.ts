import { apiRequest } from "../../../lib/http/api-client";
import { booleanValue, jsonList, jsonObject, nonNegativeInteger, nullableText, text } from "../../../lib/http/json-contract";
import type { ClosurePendingIssue, CompensationComponent, VariableCompensationItem, VariableCompensationResult } from "../types/variable-compensation";

function stringRecord(value: unknown): Readonly<Record<string, string>> {
  const root = jsonObject(value, "metadata");
  return Object.fromEntries(Object.entries(root).map(([key, entry]) => [key, text(entry, key)]));
}

function issue(value: unknown): ClosurePendingIssue {
  const item = jsonObject(value, "issue");
  return { code: text(item.code, "code"), component: text(item.component, "component") as ClosurePendingIssue["component"], scope: text(item.scope, "scope") as ClosurePendingIssue["scope"], collaborator_id: nullableText(item.collaborator_id, "collaborator_id"), affected_collaborator_ids: jsonList(item.affected_collaborator_ids, (entry) => text(entry, "collaborator_id"), "affected_collaborator_ids"), competence_month: text(item.competence_month, "competence_month"), message: text(item.message, "message"), severity: text(item.severity, "severity") as "blocking", blocking: booleanValue(item.blocking, "blocking"), action_type: nullableText(item.action_type, "action_type"), action_target: nullableText(item.action_target, "action_target"), metadata: stringRecord(item.metadata) };
}

function component(value: unknown): CompensationComponent {
  const item = jsonObject(value, "component");
  return { status: text(item.status, "status"), reference_month: text(item.reference_month, "reference_month"), eligible: booleanValue(item.eligible, "eligible"), tier: nullableText(item.tier, "tier"), amount: nullableText(item.amount, "amount"), individual_value: nullableText(item.individual_value, "individual_value"), team_average: nullableText(item.team_average, "team_average") };
}

function item(value: unknown): VariableCompensationItem {
  const root = jsonObject(value, "item");
  const csat = jsonObject(root.csat, "csat");
  const recurrence = jsonObject(root.recurrence, "recurrence");
  const delays = jsonObject(root.delays, "delays");
  const absences = jsonObject(root.absences, "absences");
  const nullableCount = (entry: unknown, field: string) => entry === null ? null : nonNegativeInteger(entry, field);
  const cap = recurrence.team_average_cap_passed;
  if (cap !== null && typeof cap !== "boolean") throw new TypeError("Invalid team_average_cap_passed");
  return {
    collaborator_id: text(root.collaborator_id, "collaborator_id"), display_name: text(root.display_name, "display_name"), status: text(root.status, "status") as VariableCompensationItem["status"], pending_reasons: jsonList(root.pending_reasons, (reason) => text(reason, "reason"), "pending_reasons"), pending_issues: jsonList(root.pending_issues, issue, "pending_issues"),
    csat: { ...component(csat), modality: text(csat.modality, "modality"), response_rate: nullableText(csat.response_rate, "response_rate"), minimum_response_rate: text(csat.minimum_response_rate, "minimum_response_rate") },
    recurrence: { ...component(recurrence), team_average_cap_passed: cap },
    delays: { count: nullableCount(delays.count, "delay count"), amount: nullableText(delays.amount, "delay amount") }, absences: { count: nullableCount(absences.count, "absence count"), amount: nullableText(absences.amount, "absence amount") }, positive_amount: nullableText(root.positive_amount, "positive_amount"), deductions_amount: nullableText(root.deductions_amount, "deductions_amount"), total_amount: nullableText(root.total_amount, "total_amount"),
  };
}

export function getVariableCompensation(filters: { competenceMonth: string; collaboratorId?: string; status?: string }, signal?: AbortSignal): Promise<VariableCompensationResult> {
  const parameters = new URLSearchParams({ competence_month: filters.competenceMonth });
  if (filters.collaboratorId) parameters.set("collaborator_id", filters.collaboratorId);
  if (filters.status) parameters.set("status", filters.status);
  return apiRequest(`/variable-compensation?${parameters}`, { signal, parse(value) { const root = jsonObject(value, "root"); const summary = jsonObject(root.issue_summary, "issue_summary"); return { competence_month: text(root.competence_month, "competence_month"), collaborator_count: nonNegativeInteger(root.collaborator_count, "collaborator_count"), calculated_count: nonNegativeInteger(root.calculated_count, "calculated_count"), incomplete_count: nonNegativeInteger(root.incomplete_count, "incomplete_count"), projected_total: nullableText(root.projected_total, "projected_total"), issue_summary: { total_count: nonNegativeInteger(summary.total_count, "total_count"), blocking_count: nonNegativeInteger(summary.blocking_count, "blocking_count"), by_component: Object.fromEntries(Object.entries(jsonObject(summary.by_component, "by_component")).map(([key, entry]) => [key, nonNegativeInteger(entry, key)])) }, issues: jsonList(root.issues, issue, "issues"), items: jsonList(root.items, item, "items") }; } });
}
