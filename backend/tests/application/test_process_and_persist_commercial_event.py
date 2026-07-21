from collections.abc import Callable, Iterator
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import TracebackType
from uuid import UUID

import pytest

from supervisor_ai.application import (
    CommercialEvent,
    CommercialEventConflict,
    LedgerConflict,
    ProcessingRun,
)
from supervisor_ai.application.use_cases import (
    CommercialEventPhase,
    PhaseResult,
    ProcessAndPersistCommercialEventCommand,
    ProcessAndPersistCommercialEventUseCase,
    ProcessCommercialEventCommand,
    ProcessCommercialEventResult,
)
from supervisor_ai.rules_engine import (
    Currency,
    EvaluationContext,
    LedgerEntry,
    LedgerEntryType,
)

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


@dataclass
class Store:
    events: dict[str, CommercialEvent] = field(default_factory=dict)
    runs: dict[str, ProcessingRun] = field(default_factory=dict)
    ledger: dict[str, LedgerEntry] = field(default_factory=dict)


class EventRepositoryFake:
    def __init__(self, store: Store, operations: list[str]) -> None:
        self.store = store
        self.operations = operations

    def add(self, event: CommercialEvent) -> None:
        self.operations.append("event.add")
        self.store.events[event.external_reference] = event

    def get_by_id(self, event_id: str) -> CommercialEvent | None:
        return next(
            (event for event in self.store.events.values() if event.id == event_id),
            None,
        )

    def get_by_external_reference(self, reference: str) -> CommercialEvent | None:
        return self.store.events.get(reference)


class ProcessingRunRepositoryFake:
    def __init__(
        self, store: Store, operations: list[str], *, fail_on_add: bool = False
    ) -> None:
        self.store = store
        self.operations = operations
        self.fail_on_add = fail_on_add

    def add(self, run: ProcessingRun) -> None:
        self.operations.append("run.add")
        if self.fail_on_add:
            raise RuntimeError("processing run persistence failed")
        self.store.runs[run.id] = run

    def get_by_id(self, run_id: str) -> ProcessingRun | None:
        return self.store.runs.get(run_id)

    def find_by_event_id(self, event_id: str) -> tuple[ProcessingRun, ...]:
        return tuple(
            run for run in self.store.runs.values() if run.event_id == event_id
        )


class LedgerRepositoryFake:
    def __init__(
        self, store: Store, operations: list[str], *, fail_on_add: bool = False
    ) -> None:
        self.store = store
        self.operations = operations
        self.fail_on_add = fail_on_add

    def add(self, entry: LedgerEntry) -> None:
        self.operations.append("ledger.add")
        if self.fail_on_add:
            raise RuntimeError("ledger persistence failed")
        self.store.ledger[entry.event_id] = entry

    def get_by_entry_id(self, entry_id: str) -> LedgerEntry | None:
        return next(
            (
                entry
                for entry in self.store.ledger.values()
                if entry.entry_id == entry_id
            ),
            None,
        )

    def find_credit_by_event_id(self, event_id: str) -> LedgerEntry | None:
        return self.store.ledger.get(event_id)


class UnitOfWorkFake:
    def __init__(
        self,
        store: Store,
        operations: list[str],
        *,
        fail_run: bool = False,
        fail_ledger: bool = False,
    ) -> None:
        self.store = store
        self.operations = operations
        self.events = EventRepositoryFake(store, operations)
        self.processing_runs = ProcessingRunRepositoryFake(
            store, operations, fail_on_add=fail_run
        )
        self.ledger = LedgerRepositoryFake(
            store, operations, fail_on_add=fail_ledger
        )
        self._snapshot: Store | None = None

    def __enter__(self) -> "UnitOfWorkFake":
        self._snapshot = deepcopy(self.store)
        self.operations.append("uow.enter")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        if exc_type is not None:
            self.rollback()
        self.operations.append("uow.exit")

    def commit(self) -> None:
        self.operations.append("uow.commit")

    def rollback(self) -> None:
        assert self._snapshot is not None
        self.store.events = self._snapshot.events
        self.store.runs = self._snapshot.runs
        self.store.ledger = self._snapshot.ledger
        self.operations.append("uow.rollback")


@dataclass
class UnitOfWorkFactoryFake:
    store: Store = field(default_factory=Store)
    operations: list[str] = field(default_factory=list)
    fail_run: bool = False
    fail_ledger: bool = False

    def __call__(self) -> UnitOfWorkFake:
        return UnitOfWorkFake(
            self.store,
            self.operations,
            fail_run=self.fail_run,
            fail_ledger=self.fail_ledger,
        )


@dataclass
class ProcessorStub:
    result: ProcessCommercialEventResult
    error: Exception | None = None
    calls: list[str] = field(default_factory=list)

    def execute(
        self, command: ProcessCommercialEventCommand
    ) -> ProcessCommercialEventResult:
        self.calls.append(command.event_id)
        if self.error is not None:
            raise self.error
        return self.result


def event(*, payload_value: str = "same") -> CommercialEvent:
    return CommercialEvent(
        id="event-1",
        external_reference="external-1",
        source="commercial-system",
        occurred_at=NOW - timedelta(hours=1),
        received_at=NOW,
        raw_payload={"value": payload_value},
        created_at=NOW,
    )


def ledger(*, amount: Decimal = Decimal("119.90")) -> LedgerEntry:
    return LedgerEntry(
        entry_id="ledger-1",
        event_id="event-1",
        beneficiary_id="employee-1",
        entry_type=LedgerEntryType.CREDIT,
        amount=amount,
        currency=Currency.BRL,
        posted_at=NOW,
        posting_reference="posting-1",
        source_reference_ids=("source-1",),
        remuneration_calculation_reference="calculation-1",
        invoice_id="invoice-1",
    )


def processing_result(
    *,
    entry: LedgerEntry | None = None,
    phases: tuple[PhaseResult, ...] | None = None,
) -> ProcessCommercialEventResult:
    completed = phases or (
        PhaseResult(
            phase=CommercialEventPhase.CONTRACT_FACTS,
            status="completed",
            output=object(),
            warnings=("warning-1",),
            audit_references=("audit-1",),
        ),
    )
    return ProcessCommercialEventResult(
        event_id="event-1",
        phase_results=completed,
        final_status=completed[-1].status,
        ledger_entry=entry,
        warnings=tuple(item for phase in completed for item in phase.warnings),
        audit_references=tuple(
            item for phase in completed for item in phase.audit_references
        ),
    )


def command(
    value: CommercialEvent | None = None,
) -> ProcessAndPersistCommercialEventCommand:
    return ProcessAndPersistCommercialEventCommand(
        event=value or event(),
        evaluation_context=EvaluationContext(
            evaluation_id=UUID("00000000-0000-0000-0000-000000000001"),
            subject_id="contract-1",
            observed_at=NOW,
            evidence=(),
        ),
        rules_engine_version="rules-1",
    )


def values[T](*items: T) -> Callable[[], T]:
    iterator: Iterator[T] = iter(items)
    return lambda: next(iterator)


def use_case(
    factory: UnitOfWorkFactoryFake,
    result: ProcessCommercialEventResult,
    *,
    processor_error: Exception | None = None,
    run_ids: tuple[str, ...] = ("run-1",),
) -> ProcessAndPersistCommercialEventUseCase:
    return ProcessAndPersistCommercialEventUseCase(
        processor=ProcessorStub(result, processor_error),
        unit_of_work_factory=factory,
        clock=values(NOW, NOW + timedelta(seconds=1)),
        processing_run_id_generator=values(*run_ids),
    )


def test_success_persists_all_facts_and_commits_once() -> None:
    factory = UnitOfWorkFactoryFake()
    entry = ledger()

    result = use_case(factory, processing_result(entry=entry)).execute(command())

    assert result.event_id == "event-1"
    assert result.processing_run_id == "run-1"
    assert result.final_status == "completed"
    assert result.event_persisted is True
    assert result.ledger_entry_id == "ledger-1"
    assert result.ledger_persisted is True
    assert result.warnings == ("warning-1",)
    assert result.audit_references == ("audit-1",)
    assert factory.store.events["external-1"] == event()
    assert factory.store.ledger["event-1"] == entry
    run = factory.store.runs["run-1"]
    assert run.phase_results == [
        {
            "phase": "contract_facts",
            "status": "completed",
            "can_continue": True,
            "warnings": ["warning-1"],
            "audit_references": ["audit-1"],
        }
    ]
    assert "output" not in run.phase_results[0]
    assert factory.operations == [
        "uow.enter",
        "event.add",
        "run.add",
        "ledger.add",
        "uow.commit",
        "uow.exit",
    ]


def test_without_ledger_persists_event_and_run() -> None:
    factory = UnitOfWorkFactoryFake()
    result = use_case(factory, processing_result()).execute(command())

    assert result.ledger_entry_id is None
    assert result.ledger_persisted is False
    assert factory.store.ledger == {}
    assert factory.operations.count("uow.commit") == 1


def test_early_stop_persists_only_executed_phases() -> None:
    phase = PhaseResult(
        phase=CommercialEventPhase.OPERATIONAL_CONTEXT,
        status="pending-review",
        output={"unsafe": object()},
        can_continue=False,
    )
    factory = UnitOfWorkFactoryFake()

    result = use_case(factory, processing_result(phases=(phase,))).execute(command())

    assert result.final_status == "pending-review"
    assert result.executed_phases == ("operational_context",)
    assert factory.store.runs["run-1"].phase_results[0]["can_continue"] is False


def test_exact_reprocessing_adds_run_but_not_event_or_ledger() -> None:
    factory = UnitOfWorkFactoryFake()
    first = use_case(factory, processing_result(entry=ledger()), run_ids=("run-1",))
    first.execute(command())
    factory.operations.clear()
    second = use_case(factory, processing_result(entry=ledger()), run_ids=("run-2",))

    result = second.execute(command())

    assert result.event_persisted is False
    assert result.ledger_persisted is False
    assert result.ledger_already_existed is True
    assert set(factory.store.runs) == {"run-1", "run-2"}
    assert len(factory.store.events) == len(factory.store.ledger) == 1
    assert "event.add" not in factory.operations
    assert "ledger.add" not in factory.operations


def test_divergent_event_conflict_rolls_back_without_run() -> None:
    factory = UnitOfWorkFactoryFake()
    factory.store.events["external-1"] = event()

    with pytest.raises(CommercialEventConflict):
        use_case(factory, processing_result()).execute(
            command(event(payload_value="different"))
        )

    assert factory.store.runs == {}
    assert "uow.commit" not in factory.operations
    assert "uow.rollback" in factory.operations


def test_divergent_ledger_rolls_back_new_run() -> None:
    factory = UnitOfWorkFactoryFake()
    factory.store.events["external-1"] = event()
    factory.store.ledger["event-1"] = ledger(amount=Decimal("10.00"))

    with pytest.raises(LedgerConflict):
        use_case(factory, processing_result(entry=ledger())).execute(command())

    assert factory.store.runs == {}
    assert "uow.commit" not in factory.operations


@pytest.mark.parametrize("failure", ["run", "ledger"])
def test_persistence_failure_rolls_back_all_new_facts(failure: str) -> None:
    factory = UnitOfWorkFactoryFake(
        fail_run=failure == "run", fail_ledger=failure == "ledger"
    )
    result = processing_result(entry=ledger())

    with pytest.raises(RuntimeError, match="persistence failed"):
        use_case(factory, result).execute(command())

    assert factory.store == Store()
    assert "uow.commit" not in factory.operations


def test_rules_engine_failure_persists_nothing() -> None:
    factory = UnitOfWorkFactoryFake()

    with pytest.raises(RuntimeError, match="rules failed"):
        use_case(
            factory,
            processing_result(),
            processor_error=RuntimeError("rules failed"),
        ).execute(command())

    assert factory.store == Store()
    assert "uow.commit" not in factory.operations


def test_clock_and_id_generator_make_result_deterministic() -> None:
    first = use_case(UnitOfWorkFactoryFake(), processing_result()).execute(command())
    second = use_case(UnitOfWorkFactoryFake(), processing_result()).execute(command())
    assert first == second


def test_rejects_naive_clock_before_persisting_run() -> None:
    factory = UnitOfWorkFactoryFake()
    case = ProcessAndPersistCommercialEventUseCase(
        processor=ProcessorStub(processing_result()),
        unit_of_work_factory=factory,
        clock=lambda: datetime(2026, 7, 21),
        processing_run_id_generator=lambda: "run-1",
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        case.execute(command())

    assert factory.store == Store()
