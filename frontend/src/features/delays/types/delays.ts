export type DelayType = "entry" | "pause_duration";
export type ReviewStatus = "pending_review" | "valid" | "corrected";

export interface EmployeeOccurrenceEvidence {
  readonly id: string;
  readonly external_reference: string;
  readonly external_collaborator_identity: string;
  readonly submitted_at: string;
  readonly occurrence_date: string;
  readonly reason_text: string;
}

export interface DelayReview {
  readonly id: string;
  readonly decision: "valid" | "corrected";
  readonly decided_at: string;
  readonly decided_by: string;
  readonly employee_occurrence_report_id: string | null;
  readonly note: string | null;
}

export interface OperationalDelay {
  readonly delay_occurrence_id: string;
  readonly collaborator_id: string;
  readonly display_name: string;
  readonly occurrence_date: string;
  readonly occurrence_type: DelayType;
  readonly review_status: ReviewStatus;
  readonly counts_for_rv: boolean;
  readonly observed_seconds: number;
  readonly applied_limit_seconds: number;
  readonly source_fact: {
    readonly queue: string;
    readonly started_at: string;
    readonly ended_at: string;
    readonly duration_seconds: number;
    readonly pause_type: string | null;
  };
  readonly schedule: null | {
    readonly planned_start: string;
    readonly planned_end: string | null;
    readonly effective_origin: string;
  };
  readonly review: DelayReview | null;
  readonly possible_employee_occurrence_reports: readonly EmployeeOccurrenceEvidence[];
}

export interface OperationalDelaysResult {
  readonly competence_month: string;
  readonly detected_count: number;
  readonly pending_count: number;
  readonly valid_count: number;
  readonly corrected_count: number;
  readonly items: readonly OperationalDelay[];
}
