from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from supervisor_ai.application.financial_snapshot import FinancialSnapshot
from supervisor_ai.rules_engine import EvaluationContext, LedgerEntry


class CommercialEventPhase(StrEnum):
    """Ordem estável das fases públicas do fluxo de remuneração."""

    CONTRACT_FACTS = "contract_facts"
    COMMERCIAL_CLASSIFICATION = "commercial_classification"
    OPERATIONAL_CONTEXT = "operational_context"
    REMUNERATION_ELIGIBILITY = "remuneration_eligibility"
    PAYMENT_VALIDATION = "payment_validation"
    REMUNERATION_AMOUNT = "remuneration_amount"
    LEDGER_POSTING = "ledger_posting"


@dataclass(frozen=True, slots=True)
class ProcessCommercialEventCommand:
    """Entrada imutável para processar um único evento comercial."""

    event_id: str
    evaluation_context: EvaluationContext
    financial_snapshot: FinancialSnapshot | None = None


@dataclass(frozen=True, slots=True)
class PhaseResult:
    """Envelope de orquestração produzido por uma fase do Rules Engine.

    ``output`` mantém o contrato público específico da fase sem obrigar a
    Application a interpretar seu conteúdo. A própria fase informa se o fluxo
    pode continuar.
    """

    phase: CommercialEventPhase
    status: str
    output: object
    can_continue: bool = True
    ledger_entry: LedgerEntry | None = None
    warnings: tuple[str, ...] = ()
    audit_references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProcessCommercialEventResult:
    """Resultado completo, determinístico e auditável da orquestração."""

    event_id: str
    phase_results: tuple[PhaseResult, ...]
    final_status: str
    ledger_entry: LedgerEntry | None
    warnings: tuple[str, ...]
    audit_references: tuple[str, ...]


class CommercialEventPhaseHandler(Protocol):
    """Porta de uma fase implementada sobre contratos públicos do Rules Engine."""

    def execute(
        self,
        command: ProcessCommercialEventCommand,
        previous_results: tuple[PhaseResult, ...],
    ) -> PhaseResult: ...


@dataclass(frozen=True, slots=True)
class _ConfiguredPhase:
    phase: CommercialEventPhase
    handler: CommercialEventPhaseHandler


class ProcessCommercialEventUseCase:
    """Orquestra o fluxo comercial sem interpretar regras ou executar I/O."""

    def __init__(
        self,
        *,
        contract_facts: CommercialEventPhaseHandler,
        commercial_classification: CommercialEventPhaseHandler,
        operational_context: CommercialEventPhaseHandler,
        remuneration_eligibility: CommercialEventPhaseHandler,
        payment_validation: CommercialEventPhaseHandler,
        remuneration_amount: CommercialEventPhaseHandler,
        ledger_posting: CommercialEventPhaseHandler,
    ) -> None:
        self._phases = (
            _ConfiguredPhase(CommercialEventPhase.CONTRACT_FACTS, contract_facts),
            _ConfiguredPhase(
                CommercialEventPhase.COMMERCIAL_CLASSIFICATION,
                commercial_classification,
            ),
            _ConfiguredPhase(
                CommercialEventPhase.OPERATIONAL_CONTEXT,
                operational_context,
            ),
            _ConfiguredPhase(
                CommercialEventPhase.REMUNERATION_ELIGIBILITY,
                remuneration_eligibility,
            ),
            _ConfiguredPhase(
                CommercialEventPhase.PAYMENT_VALIDATION,
                payment_validation,
            ),
            _ConfiguredPhase(
                CommercialEventPhase.REMUNERATION_AMOUNT,
                remuneration_amount,
            ),
            _ConfiguredPhase(CommercialEventPhase.LEDGER_POSTING, ledger_posting),
        )

    def execute(
        self, command: ProcessCommercialEventCommand
    ) -> ProcessCommercialEventResult:
        phase_results: list[PhaseResult] = []

        for configured in self._phases:
            result = configured.handler.execute(command, tuple(phase_results))
            if result.phase is not configured.phase:
                msg = (
                    f"Phase handler for {configured.phase.value!r} returned "
                    f"{result.phase.value!r}"
                )
                raise ValueError(msg)
            phase_results.append(result)
            if not result.can_continue:
                break

        completed = tuple(phase_results)
        last_result = completed[-1]
        return ProcessCommercialEventResult(
            event_id=command.event_id,
            phase_results=completed,
            final_status=last_result.status,
            ledger_entry=next(
                (
                    result.ledger_entry
                    for result in reversed(completed)
                    if result.ledger_entry is not None
                ),
                None,
            ),
            warnings=tuple(
                warning for result in completed for warning in result.warnings
            ),
            audit_references=tuple(
                reference
                for result in completed
                for reference in result.audit_references
            ),
        )
