"""Casos de uso e portas da camada Application."""

from supervisor_ai.application.errors import (
    ApplicationConflict,
    CommercialEventConflict,
    CommercialEventNotFound,
    LedgerConflict,
)
from supervisor_ai.application.financial_snapshot import (
    FinancialSnapshot,
    PaymentFacts,
    RemunerationFacts,
    RemunerationPostingFacts,
)
from supervisor_ai.application.persistence import (
    CommercialEvent,
    CommercialEventCursorPosition,
    ProcessingRun,
)
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
    "CommercialEventCursorPosition",
    "CommercialEventNotFound",
    "Clock",
    "EventRepository",
    "FinancialSnapshot",
    "LedgerRepository",
    "LedgerConflict",
    "PaymentFacts",
    "ProcessingRun",
    "ProcessingRunIdGenerator",
    "ProcessingRunRepository",
    "RemunerationFacts",
    "RemunerationPostingFacts",
    "UnitOfWork",
    "UnitOfWorkFactory",
]
