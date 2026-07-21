from datetime import UTC, datetime
from decimal import Decimal

from supervisor_ai.application import CommercialEvent, ProcessingRun
from supervisor_ai.rules_engine import Currency, LedgerEntry, LedgerEntryType


def commercial_event(
    event_id: str = "event-1",
    *,
    external_reference: str = "external-1",
) -> CommercialEvent:
    return CommercialEvent(
        id=event_id,
        external_reference=external_reference,
        source="commercial-system",
        occurred_at=datetime(2026, 7, 20, 12, 30, tzinfo=UTC),
        received_at=datetime(2026, 7, 20, 12, 31, tzinfo=UTC),
        raw_payload={"nested": {"items": [1, "two", True]}, "nullable": None},
    )


def processing_run(run_id: str, event_id: str = "event-1") -> ProcessingRun:
    return ProcessingRun(
        id=run_id,
        event_id=event_id,
        final_status="posted",
        started_at=datetime(2026, 7, 20, 12, 32, tzinfo=UTC),
        completed_at=datetime(2026, 7, 20, 12, 33, tzinfo=UTC),
        rules_engine_version="rules-1",
        phase_results=[{"phase": "classification", "status": "completed"}],
        warnings=["review-source"],
        audit_references=["audit-1"],
    )


def ledger_entry(
    entry_id: str = "ledger-1",
    event_id: str = "event-1",
    *,
    amount: Decimal = Decimal("119.90"),
    invoice_id: str | None = "invoice-1",
) -> LedgerEntry:
    return LedgerEntry(
        entry_id=entry_id,
        event_id=event_id,
        beneficiary_id="employee-1",
        entry_type=LedgerEntryType.CREDIT,
        amount=amount,
        currency=Currency.BRL,
        posted_at=datetime(2026, 7, 20, 13, 0, tzinfo=UTC),
        posting_reference="posting-1",
        source_reference_ids=("ticket-1", "invoice-1"),
        remuneration_calculation_reference="calculation-1",
        invoice_id=invoice_id,
    )
