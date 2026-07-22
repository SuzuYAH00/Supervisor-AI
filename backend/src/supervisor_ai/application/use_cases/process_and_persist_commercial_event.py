from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from supervisor_ai.application.errors import CommercialEventConflict, LedgerConflict
from supervisor_ai.application.financial_snapshot import FinancialSnapshot
from supervisor_ai.application.persistence import (
    CommercialEvent,
    JsonValue,
    ProcessingRun,
)
from supervisor_ai.application.ports import (
    Clock,
    ProcessingRunIdGenerator,
    UnitOfWork,
    UnitOfWorkFactory,
)
from supervisor_ai.application.use_cases.process_commercial_event import (
    PhaseResult,
    ProcessCommercialEventCommand,
    ProcessCommercialEventResult,
)
from supervisor_ai.rules_engine import EvaluationContext, LedgerEntry


class CommercialEventProcessor(Protocol):
    def execute(
        self, command: ProcessCommercialEventCommand
    ) -> ProcessCommercialEventResult: ...


@dataclass(frozen=True, slots=True)
class ProcessAndPersistCommercialEventCommand:
    event: CommercialEvent
    evaluation_context: EvaluationContext
    rules_engine_version: str
    financial_snapshot: FinancialSnapshot | None = None

    def __post_init__(self) -> None:
        if not self.rules_engine_version:
            raise ValueError("rules_engine_version is required")


@dataclass(frozen=True, slots=True)
class ProcessAndPersistCommercialEventResult:
    event_id: str
    processing_run_id: str
    final_status: str
    event_persisted: bool
    ledger_entry_id: str | None
    ledger_persisted: bool
    ledger_already_existed: bool
    executed_phases: tuple[str, ...]
    warnings: tuple[str, ...]
    audit_references: tuple[str, ...]


class ProcessAndPersistCommercialEventUseCase:
    """Materializa, em uma transação, os fatos produzidos pelo fluxo puro."""

    def __init__(
        self,
        *,
        processor: CommercialEventProcessor,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        processing_run_id_generator: ProcessingRunIdGenerator,
    ) -> None:
        self._processor = processor
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._processing_run_id_generator = processing_run_id_generator

    def execute(
        self, command: ProcessAndPersistCommercialEventCommand
    ) -> ProcessAndPersistCommercialEventResult:
        with self._unit_of_work_factory() as unit_of_work:
            event_persisted = self._ensure_event(unit_of_work, command.event)
            started_at = self._aware_now()
            processing_result = self._processor.execute(
                ProcessCommercialEventCommand(
                    event_id=command.event.id,
                    evaluation_context=command.evaluation_context,
                    financial_snapshot=command.financial_snapshot,
                )
            )
            if processing_result.event_id != command.event.id:
                raise ValueError("processor result belongs to a different event")
            completed_at = self._aware_now()
            run_id = self._processing_run_id_generator()
            if not run_id:
                raise ValueError("processing run id must not be empty")

            processing_run = ProcessingRun(
                id=run_id,
                event_id=command.event.id,
                final_status=processing_result.final_status,
                started_at=started_at,
                completed_at=completed_at,
                rules_engine_version=command.rules_engine_version,
                phase_results=_serialize_phase_results(
                    processing_result.phase_results
                ),
                warnings=list(processing_result.warnings),
                audit_references=list(processing_result.audit_references),
                created_at=completed_at,
            )
            unit_of_work.processing_runs.add(processing_run)
            ledger_persisted, ledger_already_existed = self._persist_ledger(
                unit_of_work, processing_result.ledger_entry
            )
            unit_of_work.commit()

            ledger_entry = processing_result.ledger_entry
            return ProcessAndPersistCommercialEventResult(
                event_id=command.event.id,
                processing_run_id=run_id,
                final_status=processing_result.final_status,
                event_persisted=event_persisted,
                ledger_entry_id=(
                    None if ledger_entry is None else ledger_entry.entry_id
                ),
                ledger_persisted=ledger_persisted,
                ledger_already_existed=ledger_already_existed,
                executed_phases=tuple(
                    phase.phase.value for phase in processing_result.phase_results
                ),
                warnings=processing_result.warnings,
                audit_references=processing_result.audit_references,
            )

    @staticmethod
    def _ensure_event(unit_of_work: UnitOfWork, event: CommercialEvent) -> bool:
        existing = unit_of_work.events.get_by_external_reference(
            event.external_reference
        )
        if existing is None:
            unit_of_work.events.add(event)
            return True
        if not _same_commercial_event(existing, event):
            raise CommercialEventConflict(
                f"external reference {event.external_reference!r} is already in use"
            )
        return False

    @staticmethod
    def _persist_ledger(
        unit_of_work: UnitOfWork, entry: LedgerEntry | None
    ) -> tuple[bool, bool]:
        if entry is None:
            return False, False
        existing = unit_of_work.ledger.find_credit_by_event_id(entry.event_id)
        if existing is None:
            unit_of_work.ledger.add(entry)
            return True, False
        if existing != entry:
            raise LedgerConflict(
                f"credit for event {entry.event_id!r} differs from persisted entry"
            )
        return False, True

    def _aware_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must return timezone-aware datetimes")
        return value


def _same_commercial_event(first: CommercialEvent, second: CommercialEvent) -> bool:
    return all(
        (
            first.id == second.id,
            first.external_reference == second.external_reference,
            first.source == second.source,
            first.occurred_at == second.occurred_at,
            first.raw_payload == second.raw_payload,
        )
    )


def _serialize_phase_results(
    phase_results: tuple[PhaseResult, ...],
) -> list[JsonValue]:
    return [
        {
            "phase": result.phase.value,
            "status": result.status,
            "can_continue": result.can_continue,
            "warnings": list(result.warnings),
            "audit_references": list(result.audit_references),
        }
        for result in phase_results
    ]
