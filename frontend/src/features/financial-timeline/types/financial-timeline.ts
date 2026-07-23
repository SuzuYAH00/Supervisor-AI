export interface FinancialTimelineFilters {
  readonly start_date: string | null;
  readonly end_date: string | null;
  readonly entry_type: string | null;
  readonly currency: string | null;
}

export interface FinancialTimelinePage {
  readonly limit: number;
  readonly next_cursor: string | null;
  readonly has_more: boolean;
}

export interface TimelineCommercialEvent {
  readonly event_id: string;
  readonly external_reference: string;
  readonly source: string;
  readonly occurred_at: string;
}

export interface FinancialTimelineItem {
  readonly ledger_entry_id: string;
  readonly posted_at: string;
  readonly entry_type: string;
  readonly amount: string;
  readonly currency: string;
  readonly invoice_id: string | null;
  readonly posting_reference: string;
  readonly remuneration_calculation_reference: string;
  readonly source_reference_ids: readonly string[];
  readonly commercial_event: TimelineCommercialEvent;
}

export interface FinancialTimeline {
  readonly collaborator_id: string;
  readonly filters: FinancialTimelineFilters;
  readonly page: FinancialTimelinePage;
  readonly items: readonly FinancialTimelineItem[];
}

export interface FinancialTimelineQuery {
  readonly startDate?: string;
  readonly endDate?: string;
  readonly entryType?: string;
  readonly currency?: string;
  readonly limit?: number;
  readonly cursor?: string;
}
