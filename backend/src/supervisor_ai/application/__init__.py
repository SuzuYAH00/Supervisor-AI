"""Casos de uso e portas da camada Application."""

from supervisor_ai.application.errors import (
    ApplicationConflict,
    CommercialEventConflict,
    LedgerConflict,
)
from supervisor_ai.application.persistence import CommercialEvent, ProcessingRun
from supervisor_ai.application.ports import (
    Clock,
    EventRepository,
    LedgerRepository,
    ProcessingRunIdGenerator,
    ProcessingRunRepository,
    UnitOfWork,
    UnitOfWorkFactory,
)

__all__ = [
    "ApplicationConflict",
    "CommercialEvent",
    "CommercialEventConflict",
    "Clock",
    "EventRepository",
    "LedgerRepository",
    "LedgerConflict",
    "ProcessingRun",
    "ProcessingRunIdGenerator",
    "ProcessingRunRepository",
    "UnitOfWork",
    "UnitOfWorkFactory",
]
