from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import CommercialEvent
from supervisor_ai.application.use_cases import (
    CommercialEventPhase,
    PhaseResult,
    ProcessAndPersistCommercialEventCommand,
    ProcessAndPersistCommercialEventUseCase,
    ProcessCommercialEventCommand,
    ProcessCommercialEventResult,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from supervisor_ai.rules_engine import (
    Currency,
    EvaluationContext,
    LedgerEntry,
    LedgerEntryType,
)

NOW = datetime(2026, 7, 21, 14, 0, tzinfo=UTC)


class ProcessorStub:
    def __init__(self, entry: LedgerEntry) -> None:
        self.entry = entry

    def execute(
        self, command: ProcessCommercialEventCommand
    ) -> ProcessCommercialEventResult:
        phase = PhaseResult(
            phase=CommercialEventPhase.LEDGER_POSTING,
            status="posted",
            output=object(),
            ledger_entry=self.entry,
            audit_references=("audit-integration",),
        )
        return ProcessCommercialEventResult(
            event_id=command.event_id,
            phase_results=(phase,),
            final_status=phase.status,
            ledger_entry=self.entry,
            warnings=(),
            audit_references=phase.audit_references,
        )


def clock() -> Iterator[datetime]:
    yield NOW
    yield NOW + timedelta(seconds=1)


def test_application_and_sqlalchemy_persist_complete_transaction(
    session_factory: sessionmaker[Session],
) -> None:
    event = CommercialEvent(
        id="event-integration",
        external_reference="external-integration",
        source="test-source",
        occurred_at=NOW - timedelta(days=1),
        received_at=NOW,
        raw_payload={"contract": "contract-1", "amount": "119.90"},
        created_at=NOW,
    )
    entry = LedgerEntry(
        entry_id="ledger-integration",
        event_id=event.id,
        beneficiary_id="employee-1",
        entry_type=LedgerEntryType.CREDIT,
        amount=Decimal("119.90"),
        currency=Currency.BRL,
        posted_at=NOW,
        posting_reference="posting-integration",
        source_reference_ids=("source-integration",),
        remuneration_calculation_reference="calculation-integration",
    )
    times = clock()
    use_case = ProcessAndPersistCommercialEventUseCase(
        processor=ProcessorStub(entry),
        unit_of_work_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        clock=lambda: next(times),
        processing_run_id_generator=lambda: "run-integration",
    )

    result = use_case.execute(
        ProcessAndPersistCommercialEventCommand(
            event=event,
            evaluation_context=EvaluationContext(
                evaluation_id=UUID("00000000-0000-0000-0000-000000000001"),
                subject_id="contract-1",
                observed_at=NOW,
                evidence=(),
            ),
            rules_engine_version="rules-integration",
        )
    )

    assert result.ledger_persisted is True
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.events.get_by_id(event.id) == event
        run = unit_of_work.processing_runs.get_by_id("run-integration")
        assert run is not None
        assert run.event_id == event.id
        assert run.final_status == "posted"
        assert run.audit_references == ["audit-integration"]
        assert unit_of_work.ledger.get_by_entry_id(entry.entry_id) == entry
