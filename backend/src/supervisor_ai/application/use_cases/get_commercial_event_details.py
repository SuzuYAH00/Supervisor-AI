from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from supervisor_ai.application.errors import CommercialEventNotFound
from supervisor_ai.application.persistence import CommercialEvent, ProcessingRun
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.rules_engine import Currency, LedgerEntry, LedgerEntryType

MAX_COMMERCIAL_EVENT_ID_LENGTH = 128


@dataclass(frozen=True, slots=True)
class GetCommercialEventDetailsQuery:
    commercial_event_id: str

    def __post_init__(self) -> None:
        if not self.commercial_event_id.strip():
            raise ValueError("commercial_event_id must not be blank")
        if len(self.commercial_event_id) > MAX_COMMERCIAL_EVENT_ID_LENGTH:
            raise ValueError(
                "commercial_event_id must not exceed "
                f"{MAX_COMMERCIAL_EVENT_ID_LENGTH} characters"
            )


@dataclass(frozen=True, slots=True)
class CommercialEventDetails:
    event_id: str
    external_reference: str
    source: str
    occurred_at: datetime
    received_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CommercialEventLedgerEntry:
    ledger_entry_id: str
    event_id: str
    beneficiary_id: str
    entry_type: LedgerEntryType
    amount: Decimal
    currency: Currency
    posted_at: datetime
    posting_reference: str
    remuneration_calculation_reference: str
    invoice_id: str | None
    source_reference_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommercialEventProcessingRun:
    processing_run_id: str
    event_id: str
    final_status: str
    started_at: datetime
    completed_at: datetime
    rules_engine_version: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class GetCommercialEventDetailsResult:
    commercial_event: CommercialEventDetails
    ledger_entries: tuple[CommercialEventLedgerEntry, ...]
    processing_runs: tuple[CommercialEventProcessingRun, ...]


class GetCommercialEventDetailsUseCase:
    """Consulta a trilha persistida de um evento sem reexecutar regras."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, query: GetCommercialEventDetailsQuery
    ) -> GetCommercialEventDetailsResult:
        with self._unit_of_work_factory() as unit_of_work:
            event = unit_of_work.events.get_by_id(query.commercial_event_id)
            if event is None:
                raise CommercialEventNotFound(query.commercial_event_id)
            ledger_entries = unit_of_work.ledger.find_by_event_id(
                query.commercial_event_id
            )
            processing_runs = unit_of_work.processing_runs.find_by_event_id(
                query.commercial_event_id
            )
        return GetCommercialEventDetailsResult(
            commercial_event=_event_details(event),
            ledger_entries=tuple(
                _ledger_details(entry)
                for entry in sorted(
                    ledger_entries, key=lambda item: (item.posted_at, item.entry_id)
                )
            ),
            processing_runs=tuple(
                _run_details(run)
                for run in sorted(
                    processing_runs, key=lambda item: (item.started_at, item.id)
                )
            ),
        )


def _event_details(event: CommercialEvent) -> CommercialEventDetails:
    return CommercialEventDetails(
        event_id=event.id,
        external_reference=event.external_reference,
        source=event.source,
        occurred_at=event.occurred_at,
        received_at=event.received_at,
        created_at=event.created_at,
    )


def _ledger_details(entry: LedgerEntry) -> CommercialEventLedgerEntry:
    return CommercialEventLedgerEntry(
        ledger_entry_id=entry.entry_id,
        event_id=entry.event_id,
        beneficiary_id=entry.beneficiary_id,
        entry_type=entry.entry_type,
        amount=entry.amount,
        currency=entry.currency,
        posted_at=entry.posted_at,
        posting_reference=entry.posting_reference,
        remuneration_calculation_reference=entry.remuneration_calculation_reference,
        invoice_id=entry.invoice_id,
        source_reference_ids=entry.source_reference_ids,
    )


def _run_details(run: ProcessingRun) -> CommercialEventProcessingRun:
    return CommercialEventProcessingRun(
        processing_run_id=run.id,
        event_id=run.event_id,
        final_status=run.final_status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        rules_engine_version=run.rules_engine_version,
        created_at=run.created_at,
    )
