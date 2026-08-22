export interface CompensationComponent {
  readonly status: string;
  readonly reference_month: string;
  readonly eligible: boolean;
  readonly tier: string | null;
  readonly amount: string | null;
  readonly individual_value: string | null;
  readonly team_average: string | null;
}

export interface VariableCompensationItem {
  readonly collaborator_id: string;
  readonly display_name: string;
  readonly status: "calculated" | "incomplete";
  readonly pending_reasons: readonly string[];
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
  readonly items: readonly VariableCompensationItem[];
}
