from datetime import date, datetime
from types import TracebackType
from typing import Protocol, Self

from supervisor_ai.application.persistence import CommercialEvent, ProcessingRun
from supervisor_ai.rules_engine import LedgerEntry


class EventRepository(Protocol):
    def add(self, event: CommercialEvent) -> None: ...

    def get_by_id(self, event_id: str) -> CommercialEvent | None: ...

    def get_by_external_reference(
        self, external_reference: str
    ) -> CommercialEvent | None: ...


class ProcessingRunRepository(Protocol):
    def add(self, run: ProcessingRun) -> None: ...

    def get_by_id(self, run_id: str) -> ProcessingRun | None: ...

    def find_by_event_id(self, event_id: str) -> tuple[ProcessingRun, ...]: ...


class LedgerRepository(Protocol):
    def add(self, entry: LedgerEntry) -> None: ...

    def get_by_entry_id(self, entry_id: str) -> LedgerEntry | None: ...

    def find_credit_by_event_id(self, event_id: str) -> LedgerEntry | None: ...

    def find_credits(
        self,
        *,
        beneficiary_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[LedgerEntry, ...]: ...


class UnitOfWork(Protocol):
    events: EventRepository
    processing_runs: ProcessingRunRepository
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
