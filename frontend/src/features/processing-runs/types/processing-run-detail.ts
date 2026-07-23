export interface ProcessingRunDetail {
  readonly processing_run_id: string;
  readonly event_id: string;
  readonly final_status: string;
  readonly started_at: string;
  readonly completed_at: string;
  readonly rules_engine_version: string;
  readonly created_at: string;
}

export interface ProcessingRunCommercialEvent {
  readonly event_id: string;
  readonly external_reference: string;
  readonly source: string;
  readonly occurred_at: string;
}

export interface ProcessingRunPhase {
  readonly phase: string;
  readonly status: string;
  readonly can_continue: boolean;
}

export interface ProcessingRunDetailResponse {
  readonly processing_run: ProcessingRunDetail;
  readonly commercial_event: ProcessingRunCommercialEvent;
  readonly phases: readonly ProcessingRunPhase[];
}
