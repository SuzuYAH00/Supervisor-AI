import { apiRequest } from "../../../lib/http/api-client";

export interface ImportDefinition { type: string; label: string; source: string; status: "ready" | "not_ready"; requires_competence: boolean; accepted_extensions: readonly string[]; not_ready_reason: string | null }
export interface ImportIssue { code: string; message: string; row: number | null; raw_value: string | null; external_identity: string | null }
export interface ImportResult { import_type: string; source: string; filename: string; competence_month: string | null; status: "success" | "success_with_warnings"; total_records: number; accepted_records: number; duplicate_records: number; rejected_records: number; conflict_records: number; unknown_aliases: readonly string[]; issues: readonly ImportIssue[]; coverages: readonly { dataset: string; source: string; covered_through: string }[] }
export interface ImportCatalog { items: readonly ImportDefinition[]; history_available: boolean }

const object = (value: unknown): Record<string, unknown> => { if (typeof value !== "object" || value === null || Array.isArray(value)) throw new TypeError("Invalid response"); return value as Record<string, unknown>; };
const text = (value: unknown): string => { if (typeof value !== "string") throw new TypeError("Invalid text"); return value; };
const number = (value: unknown): number => { if (typeof value !== "number") throw new TypeError("Invalid number"); return value; };
const nullableText = (value: unknown): string | null => value === null ? null : text(value);

export function getOperationalImportCatalog(signal?: AbortSignal): Promise<ImportCatalog> {
  return apiRequest("/operational-imports", { signal, parse(value) { const root = object(value); return { history_available: Boolean(root.history_available), items: (root.items as unknown[]).map((raw) => { const item = object(raw); return { type: text(item.type), label: text(item.label), source: text(item.source), status: text(item.status) as ImportDefinition["status"], requires_competence: Boolean(item.requires_competence), accepted_extensions: (item.accepted_extensions as unknown[]).map(text), not_ready_reason: nullableText(item.not_ready_reason) }; }) }; } });
}

export function uploadOperationalImport(type: string, file: File, competenceMonth?: string, signal?: AbortSignal): Promise<ImportResult> {
  const body = new FormData(); body.set("file", file); if (competenceMonth) body.set("competence_month", competenceMonth);
  return apiRequest(`/operational-imports/${encodeURIComponent(type)}`, { method: "POST", body, signal, parse(value) { const root = object(value); return { import_type: text(root.import_type), source: text(root.source), filename: text(root.filename), competence_month: nullableText(root.competence_month), status: text(root.status) as ImportResult["status"], total_records: number(root.total_records), accepted_records: number(root.accepted_records), duplicate_records: number(root.duplicate_records), rejected_records: number(root.rejected_records), conflict_records: number(root.conflict_records), unknown_aliases: (root.unknown_aliases as unknown[]).map(text), issues: (root.issues as unknown[]).map((raw) => { const issue = object(raw); return { code: text(issue.code), message: text(issue.message), row: issue.row === null ? null : number(issue.row), raw_value: nullableText(issue.raw_value), external_identity: nullableText(issue.external_identity) }; }), coverages: (root.coverages as unknown[]).map((raw) => { const coverage = object(raw); return { dataset: text(coverage.dataset), source: text(coverage.source), covered_through: text(coverage.covered_through) }; }) }; } });
}
