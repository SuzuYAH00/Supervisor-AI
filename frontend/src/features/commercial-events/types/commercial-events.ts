export interface CommercialEventListFilters {
  readonly source: string | null;
  readonly external_reference: string | null;
  readonly start_date: string | null;
  readonly end_date: string | null;
}

export interface CommercialEventCursorPage {
  readonly limit: number;
  readonly next_cursor: string | null;
  readonly has_more: boolean;
}

export interface CommercialEventListItem {
  readonly event_id: string;
  readonly external_reference: string;
  readonly source: string;
  readonly occurred_at: string;
  readonly received_at: string;
  readonly created_at: string;
}

export interface CommercialEventList {
  readonly filters: CommercialEventListFilters;
  readonly page: CommercialEventCursorPage;
  readonly items: readonly CommercialEventListItem[];
}

export interface CommercialEventsQuery {
  readonly source?: string;
  readonly externalReference?: string;
  readonly startDate?: string;
  readonly endDate?: string;
  readonly limit?: number;
  readonly cursor?: string;
}
