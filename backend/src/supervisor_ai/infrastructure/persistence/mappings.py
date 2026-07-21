from copy import deepcopy

from supervisor_ai.application.persistence import CommercialEvent, ProcessingRun
from supervisor_ai.infrastructure.persistence.models import (
    CommercialEventRecord,
    LedgerEntryRecord,
    ProcessingRunRecord,
)
from supervisor_ai.rules_engine import Currency, LedgerEntry, LedgerEntryType


def event_to_record(event: CommercialEvent) -> CommercialEventRecord:
    return CommercialEventRecord(
        id=event.id,
        external_reference=event.external_reference,
        source=event.source,
        occurred_at=event.occurred_at,
        received_at=event.received_at,
        raw_payload=deepcopy(event.raw_payload),
        created_at=event.created_at,
    )


def record_to_event(record: CommercialEventRecord) -> CommercialEvent:
    return CommercialEvent(
        id=record.id,
        external_reference=record.external_reference,
        source=record.source,
        occurred_at=record.occurred_at,
        received_at=record.received_at,
        raw_payload=deepcopy(record.raw_payload),
        created_at=record.created_at,
    )


def processing_run_to_record(run: ProcessingRun) -> ProcessingRunRecord:
    return ProcessingRunRecord(
        id=run.id,
        event_id=run.event_id,
        final_status=run.final_status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        rules_engine_version=run.rules_engine_version,
        phase_results=deepcopy(run.phase_results),
        warnings=deepcopy(run.warnings),
        audit_references=deepcopy(run.audit_references),
        created_at=run.created_at,
    )


def record_to_processing_run(record: ProcessingRunRecord) -> ProcessingRun:
    return ProcessingRun(
        id=record.id,
        event_id=record.event_id,
        final_status=record.final_status,
        started_at=record.started_at,
        completed_at=record.completed_at,
        rules_engine_version=record.rules_engine_version,
        phase_results=deepcopy(record.phase_results),
        warnings=deepcopy(record.warnings),
        audit_references=deepcopy(record.audit_references),
        created_at=record.created_at,
    )


def ledger_entry_to_record(entry: LedgerEntry) -> LedgerEntryRecord:
    return LedgerEntryRecord(
        entry_id=entry.entry_id,
        event_id=entry.event_id,
        beneficiary_id=entry.beneficiary_id,
        entry_type=entry.entry_type.value,
        amount=entry.amount,
        currency=entry.currency.value,
        posted_at=entry.posted_at,
        posting_reference=entry.posting_reference,
        source_reference_ids=list(entry.source_reference_ids),
        remuneration_calculation_reference=(
            entry.remuneration_calculation_reference
        ),
        invoice_id=entry.invoice_id,
    )


def record_to_ledger_entry(record: LedgerEntryRecord) -> LedgerEntry:
    return LedgerEntry(
        entry_id=record.entry_id,
        event_id=record.event_id,
        beneficiary_id=record.beneficiary_id,
        entry_type=LedgerEntryType(record.entry_type),
        amount=record.amount,
        currency=Currency(record.currency),
        posted_at=record.posted_at,
        posting_reference=record.posting_reference,
        source_reference_ids=tuple(record.source_reference_ids),
        remuneration_calculation_reference=(
            record.remuneration_calculation_reference
        ),
        invoice_id=record.invoice_id,
    )
