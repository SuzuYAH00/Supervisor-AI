export interface FinancialSummaryFilters {
  readonly collaborator_id: string | null;
  readonly start_date: string | null;
  readonly end_date: string | null;
}

export interface CurrencyTotal {
  readonly currency: string;
  readonly amount: string;
}

export interface CollaboratorCurrencySummary {
  readonly currency: string;
  readonly amount: string;
  readonly credit_count: number;
  readonly rank: number;
  readonly share_percentage: string;
}

export interface CollaboratorFinancialSummary {
  readonly collaborator_id: string;
  readonly credit_count: number;
  readonly totals_by_currency: readonly CollaboratorCurrencySummary[];
}

export interface FinancialSummary {
  readonly filters: FinancialSummaryFilters;
  readonly collaborator_count: number;
  readonly credit_count: number;
  readonly totals_by_currency: readonly CurrencyTotal[];
  readonly collaborators: readonly CollaboratorFinancialSummary[];
}

export interface FinancialSummaryQuery {
  readonly collaboratorId?: string;
  readonly startDate?: string;
  readonly endDate?: string;
}
