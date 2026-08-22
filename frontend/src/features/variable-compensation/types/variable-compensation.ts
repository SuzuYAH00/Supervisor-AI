export interface CompensationComponent {
  readonly status: string;
  readonly reference_month: string;
  readonly eligible: boolean;
  readonly tier: string | null;
  readonly amount: string | null;
  readonly individual_value: string | null;
  readonly team_average: string | null;
}

export interface ClosurePendingIssue {
  readonly code: string;
  readonly component: "presence" | "csat" | "recurrence" | "delays" | "work_schedule";
  readonly scope: "collaborator" | "competence";
  readonly collaborator_id: string | null;
  readonly affected_collaborator_ids: readonly string[];
  readonly competence_month: string;
  readonly message: string;
  readonly severity: "blocking";
  readonly blocking: boolean;
  readonly action_type: string | null;
  readonly action_target: string | null;
  readonly metadata: Readonly<Record<string, string>>;
}

export interface VariableCompensationItem {
  readonly collaborator_id: string;
  readonly display_name: string;
  readonly status: "calculated" | "incomplete";
  readonly pending_reasons: readonly string[];
  readonly pending_issues: readonly ClosurePendingIssue[];
  readonly csat: CompensationComponent & { readonly modality: string; readonly response_rate: string | null; readonly minimum_response_rate: string };
  readonly recurrence: CompensationComponent & { readonly team_average_cap_passed: boolean | null };
  readonly delays: { readonly count: number | null; readonly amount: string | null };
  readonly absences: { readonly count: number | null; readonly amount: string | null };
  readonly positive_amount: string | null;
  readonly deductions_amount: string | null;
  readonly total_amount: string | null;
}

export interface VariableCompensationResult {
  readonly competence_month: string;
  readonly collaborator_count: number;
  readonly calculated_count: number;
  readonly incomplete_count: number;
  readonly projected_total: string | null;
  readonly issue_summary: {
    readonly total_count: number;
    readonly blocking_count: number;
    readonly by_component: Readonly<Record<string, number>>;
  };
  readonly issues: readonly ClosurePendingIssue[];
  readonly items: readonly VariableCompensationItem[];
}
