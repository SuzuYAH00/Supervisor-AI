import ast
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from supervisor_ai.application.use_cases.process_commercial_event import (
    CommercialEventPhase,
    PhaseResult,
    ProcessCommercialEventCommand,
    ProcessCommercialEventUseCase,
)
from supervisor_ai.rules_engine import (
    Currency,
    EvaluationContext,
    LedgerEntry,
    LedgerEntryType,
)

PHASES = tuple(CommercialEventPhase)


@dataclass
class PhaseSpy:
    phase: CommercialEventPhase
    status: str = "arbitrary-status"
    can_continue: bool = True
    warnings: tuple[str, ...] = ()
    audit_references: tuple[str, ...] = ()
    ledger_entry: LedgerEntry | None = None
    calls: list[tuple[str, tuple[CommercialEventPhase, ...]]] = field(
        default_factory=list
    )

    def execute(
        self,
        command: ProcessCommercialEventCommand,
        previous_results: tuple[PhaseResult, ...],
    ) -> PhaseResult:
        self.calls.append(
            (command.event_id, tuple(result.phase for result in previous_results))
        )
        return PhaseResult(
            phase=self.phase,
            status=self.status,
            output=(command.event_id, self.phase.value),
            can_continue=self.can_continue,
            ledger_entry=self.ledger_entry,
            warnings=self.warnings,
            audit_references=self.audit_references,
        )


class FailingPhase(PhaseSpy):
    def execute(
        self,
        command: ProcessCommercialEventCommand,
        previous_results: tuple[PhaseResult, ...],
    ) -> PhaseResult:
        del command, previous_results
        raise RuntimeError("rules engine failed")


def command() -> ProcessCommercialEventCommand:
    context = EvaluationContext(
        evaluation_id=UUID("00000000-0000-0000-0000-000000000001"),
        subject_id="contract-1",
        observed_at=datetime(2026, 7, 21, tzinfo=UTC),
        evidence=(),
    )
    return ProcessCommercialEventCommand(event_id="event-1", evaluation_context=context)


def use_case(handlers: dict[CommercialEventPhase, PhaseSpy]):
    return ProcessCommercialEventUseCase(
        contract_facts=handlers[CommercialEventPhase.CONTRACT_FACTS],
        commercial_classification=handlers[
            CommercialEventPhase.COMMERCIAL_CLASSIFICATION
        ],
        operational_context=handlers[CommercialEventPhase.OPERATIONAL_CONTEXT],
        remuneration_eligibility=handlers[
            CommercialEventPhase.REMUNERATION_ELIGIBILITY
        ],
        payment_validation=handlers[CommercialEventPhase.PAYMENT_VALIDATION],
        remuneration_amount=handlers[CommercialEventPhase.REMUNERATION_AMOUNT],
        ledger_posting=handlers[CommercialEventPhase.LEDGER_POSTING],
    )


def handlers() -> dict[CommercialEventPhase, PhaseSpy]:
    return {phase: PhaseSpy(phase) for phase in PHASES}


def test_executes_phases_in_declared_order_and_passes_previous_results() -> None:
    spies = handlers()

    result = use_case(spies).execute(command())

    assert tuple(item.phase for item in result.phase_results) == PHASES
    for index, phase in enumerate(PHASES):
        assert spies[phase].calls == [("event-1", PHASES[:index])]


def test_stops_immediately_when_phase_disallows_continuation() -> None:
    spies = handlers()
    stopping_phase = CommercialEventPhase.OPERATIONAL_CONTEXT
    spies[stopping_phase].status = "pending-review"
    spies[stopping_phase].can_continue = False

    result = use_case(spies).execute(command())

    assert tuple(item.phase for item in result.phase_results) == PHASES[:3]
    assert result.final_status == "pending-review"
    assert all(not spies[phase].calls for phase in PHASES[3:])


def test_propagates_phase_errors_without_converting_them_to_business_results() -> None:
    spies = handlers()
    failing_phase = CommercialEventPhase.PAYMENT_VALIDATION
    spies[failing_phase] = FailingPhase(failing_phase)

    with pytest.raises(RuntimeError, match="rules engine failed"):
        use_case(spies).execute(command())

    assert all(not spies[phase].calls for phase in PHASES[5:])


def test_same_inputs_produce_equal_results() -> None:
    first_spies = handlers()
    second_spies = handlers()
    for spies in (first_spies, second_spies):
        spies[CommercialEventPhase.CONTRACT_FACTS].warnings = ("warning-a",)
        spies[CommercialEventPhase.LEDGER_POSTING].audit_references = ("audit-z",)

    first = use_case(first_spies).execute(command())
    second = use_case(second_spies).execute(command())

    assert first == second


def test_aggregates_metadata_without_interpreting_or_reordering_it() -> None:
    spies = handlers()
    spies[CommercialEventPhase.CONTRACT_FACTS].warnings = ("same", "first")
    spies[CommercialEventPhase.COMMERCIAL_CLASSIFICATION].warnings = ("same",)
    spies[CommercialEventPhase.OPERATIONAL_CONTEXT].audit_references = ("b", "a")

    result = use_case(spies).execute(command())

    assert result.warnings == ("same", "first", "same")
    assert result.audit_references == ("b", "a")


def test_returns_ledger_entry_produced_by_ledger_phase() -> None:
    spies = handlers()
    entry = LedgerEntry(
        entry_id="ledger-1",
        event_id="event-1",
        beneficiary_id="employee-1",
        entry_type=LedgerEntryType.CREDIT,
        amount=Decimal("125.00"),
        currency=Currency.BRL,
        posted_at=datetime(2026, 7, 21, tzinfo=UTC),
        posting_reference="posting-1",
        source_reference_ids=("source-1",),
        remuneration_calculation_reference="calculation-1",
    )
    ledger_spy = spies[CommercialEventPhase.LEDGER_POSTING]
    ledger_spy.ledger_entry = entry

    result = use_case(spies).execute(command())

    assert result.ledger_entry is entry


def test_application_use_case_has_no_infrastructure_imports() -> None:
    module_path = (
        Path(__file__).parents[2]
        / "src/supervisor_ai/application/use_cases/process_commercial_event.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    forbidden = {"fastapi", "sqlalchemy", "psycopg", "csv", "pathlib"}
    assert imported_modules.isdisjoint(forbidden)
    assert all("database" not in name for name in imported_modules)
    assert all("connectors" not in name for name in imported_modules)


def test_continuation_is_explicit_and_independent_from_business_status_names() -> None:
    spies = handlers()
    spies[CommercialEventPhase.CONTRACT_FACTS].status = "not-eligible-like-name"

    result = use_case(spies).execute(command())

    assert len(result.phase_results) == len(PHASES)
    assert result.final_status == "arbitrary-status"


def test_rejects_a_handler_result_for_a_different_phase() -> None:
    spies = handlers()
    spies[CommercialEventPhase.CONTRACT_FACTS].phase = (
        CommercialEventPhase.COMMERCIAL_CLASSIFICATION
    )

    with pytest.raises(ValueError, match="contract_facts"):
        use_case(spies).execute(command())
