"""Casos de uso e portas da camada Application."""

from supervisor_ai.application.errors import (
    ApplicationConflict,
    CommercialEventConflict,
    CommercialEventNotFound,
    LedgerConflict,
    ProcessingRunNotFound,
)
from supervisor_ai.application.financial_snapshot import (
    FinancialSnapshot,
    PaymentFacts,
    RemunerationFacts,
    RemunerationPostingFacts,
)
from supervisor_ai.application.persistence import (
    CollaboratorFinancialTimelineCursorPosition,
    CollaboratorFinancialTimelineRecord,
    CommercialEvent,
    CommercialEventCursorPosition,
    ProcessingHealthCount,
    ProcessingHealthRecord,
    ProcessingRun,
    ProcessingRunCursorPosition,
    ProcessingRunListRecord,
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
    "CollaboratorFinancialTimelineCursorPosition",
    "CollaboratorFinancialTimelineRecord",
    "CommercialEventNotFound",
    "Clock",
    "EventRepository",
    "FinancialSnapshot",
    "LedgerRepository",
    "LedgerConflict",
    "PaymentFacts",
    "ProcessingRun",
    "ProcessingHealthCount",
    "ProcessingHealthRecord",
    "ProcessingRunCursorPosition",
    "ProcessingRunListRecord",
    "ProcessingRunNotFound",
    "ProcessingRunIdGenerator",
    "ProcessingRunRepository",
    "RemunerationFacts",
    "RemunerationPostingFacts",
    "UnitOfWork",
    "UnitOfWorkFactory",
]
