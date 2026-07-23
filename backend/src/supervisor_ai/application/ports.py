from datetime import date, datetime
from types import TracebackType
from typing import Protocol, Self

from supervisor_ai.application.persistence import (
    CollaboratorFinancialTimelineCursorPosition,
    CollaboratorFinancialTimelineRecord,
    CommercialEvent,
    CommercialEventCursorPosition,
    ProcessingHealthRecord,
    ProcessingRun,
)
from supervisor_ai.rules_engine import Currency, LedgerEntry, LedgerEntryType


class EventRepository(Protocol):
    def add(self, event: CommercialEvent) -> None: ...

    def get_by_id(self, event_id: str) -> CommercialEvent | None: ...

    def get_by_external_reference(
        self, external_reference: str
    ) -> CommercialEvent | None: ...

    def search(
        self,
        *,
        source: str | None,
        external_reference: str | None,
        start_date: date | None,
        end_date: date | None,
        after: CommercialEventCursorPosition | None,
        limit: int,
    ) -> tuple[CommercialEvent, ...]: ...


class ProcessingRunRepository(Protocol):
    def add(self, run: ProcessingRun) -> None: ...

    def get_by_id(self, run_id: str) -> ProcessingRun | None: ...

    def find_by_event_id(self, event_id: str) -> tuple[ProcessingRun, ...]: ...


class ProcessingHealthRepository(Protocol):
    def get_processing_health(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
        rules_engine_version: str | None,
    ) -> ProcessingHealthRecord: ...


class LedgerRepository(Protocol):
    def add(self, entry: LedgerEntry) -> None: ...

    def get_by_entry_id(self, entry_id: str) -> LedgerEntry | None: ...

    def find_credit_by_event_id(self, event_id: str) -> LedgerEntry | None: ...

    def find_by_event_id(self, event_id: str) -> tuple[LedgerEntry, ...]: ...

    def find_credits(
        self,
        *,
        beneficiary_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[LedgerEntry, ...]: ...

    def search_collaborator_timeline(
        self,
        *,
        collaborator_id: str,
        start_date: date | None,
        end_date: date | None,
        entry_type: LedgerEntryType | None,
        currency: Currency | None,
        after: CollaboratorFinancialTimelineCursorPosition | None,
        limit: int,
    ) -> tuple[CollaboratorFinancialTimelineRecord, ...]: ...


class UnitOfWork(Protocol):
    events: EventRepository
    processing_runs: ProcessingRunRepository
    processing_health: ProcessingHealthRepository
    ledger: LedgerRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...


class ProcessingRunIdGenerator(Protocol):
    def __call__(self) -> str: ...
