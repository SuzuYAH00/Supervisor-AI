export type ScheduleStatus =
  | "resolved_standard"
  | "resolved_explicit_grid"
  | "resolved_override"
  | "unresolved";

export interface ScheduleOverride {
  readonly id: string;
  readonly collaborator_id: string;
  readonly work_date: string;
  readonly planned_start: string;
  readonly planned_end: string;
  readonly reason: string;
  readonly created_by: string;
  readonly created_at: string;
}

export interface WorkScheduleItem {
  readonly collaborator_id: string;
  readonly display_name: string;
  readonly work_date: string;
  readonly planned_start: string | null;
  readonly planned_end: string | null;
  readonly resolution_status: ScheduleStatus;
  readonly effective_origin: string;
  readonly source: string;
  readonly source_reference: string;
  readonly source_sheet: string;
  readonly source_cell: string;
  readonly unresolved_reason: string | null;
  readonly has_override: boolean;
  readonly override: ScheduleOverride | null;
}

export interface WorkSchedulesResult {
  readonly competence_month: string;
  readonly total_count: number;
  readonly pending_count: number;
  readonly items: readonly WorkScheduleItem[];
}

export interface WorkScheduleFilters {
  readonly competenceMonth: string;
  readonly collaboratorId?: string;
  readonly resolutionStatus?: string;
}

export interface OverrideInput {
  readonly collaborator_id: string;
  readonly work_date: string;
  readonly planned_start: string;
  readonly planned_end: string;
  readonly reason: string;
}
