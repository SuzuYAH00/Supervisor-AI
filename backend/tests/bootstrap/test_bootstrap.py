from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import Engine

from supervisor_ai.application import CommercialEvent
from supervisor_ai.application.use_cases import (
    CommercialEventPhase,
    GetFinancialSnapshotUseCase,
    ProcessAndPersistCommercialEventCommand,
    ProcessAndPersistCommercialEventUseCase,
    ProcessCommercialEventCommand,
    ProcessCommercialEventUseCase,
)
from supervisor_ai.bootstrap import (
    build_csv_import_service,
    build_financial_snapshot_service,
    build_rules_engine,
    build_session_factory,
    build_transactional_processor,
    build_unit_of_work_factory,
)
from supervisor_ai.database.base import Base
from supervisor_ai.infrastructure.importing import CsvImportService
from supervisor_ai.infrastructure.runtime import (
    SystemClock,
    UuidProcessingRunIdGenerator,
)
from supervisor_ai.rules_engine import (
    ContractualEvidenceName,
    EvaluationContext,
    Evidence,
    EvidenceValue,
)

NOW = datetime(2026, 7, 21, 15, 0, tzinfo=UTC)


class FixedClock:
    def __call__(self) -> datetime:
        return NOW


class FixedRunIdGenerator:
    def __call__(self) -> str:
        return "run-bootstrap"


def context() -> EvaluationContext:
    values: tuple[tuple[ContractualEvidenceName, EvidenceValue], ...] = (
        (ContractualEvidenceName.PREVIOUS_SPEED, 500),
        (ContractualEvidenceName.CURRENT_SPEED, 1000),
        (ContractualEvidenceName.PREVIOUS_PLAN_MODALITY, "standard"),
        (ContractualEvidenceName.CURRENT_PLAN_MODALITY, "standard"),
        (ContractualEvidenceName.PREVIOUS_MESH_ENABLED, False),
        (ContractualEvidenceName.CURRENT_MESH_ENABLED, False),
        (ContractualEvidenceName.PREVIOUS_ADDITIONALS, ()),
        (ContractualEvidenceName.CURRENT_ADDITIONALS, ()),
        (ContractualEvidenceName.PREVIOUS_RECURRING_VALUE, Decimal("89.90")),
        (ContractualEvidenceName.CURRENT_RECURRING_VALUE, Decimal("99.90")),
    )
    return EvaluationContext(
        evaluation_id=UUID("00000000-0000-0000-0000-000000000001"),
        subject_id="contract-bootstrap",
        observed_at=NOW,
        evidence=tuple(
            Evidence(
                evidence_id=f"evidence-{index}",
                name=name,
                value=value,
                observed_at=NOW,
            )
            for index, (name, value) in enumerate(values)
        ),
    )


def commercial_event() -> CommercialEvent:
    return CommercialEvent(
        id="event-bootstrap",
        external_reference="external-bootstrap",
        source="bootstrap-test",
        occurred_at=NOW - timedelta(hours=1),
        received_at=NOW,
        raw_payload={"contract_id": "contract-bootstrap"},
        created_at=NOW,
    )


def test_build_rules_engine_constructs_every_handler() -> None:
    processor = build_rules_engine()

    result = processor.execute(
        ProcessCommercialEventCommand(
            event_id="event-bootstrap", evaluation_context=context()
        )
    )

    assert isinstance(processor, ProcessCommercialEventUseCase)
    assert tuple(phase.phase for phase in result.phase_results) == tuple(
        CommercialEventPhase
    )
    assert result.final_status == "not_evaluable"
    assert result.ledger_entry is None


def test_runtime_dependencies_implement_stable_contracts() -> None:
    current = SystemClock()()
    generated = UuidProcessingRunIdGenerator()()

    assert current.tzinfo is not None
    assert current.utcoffset() is not None
    assert UUID(generated).version == 4


def test_build_transactional_processor_runs_with_temporary_sqlite(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'bootstrap.sqlite3'}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)

    processor = build_transactional_processor(
        database_url,
        clock=FixedClock(),
        processing_run_id_generator=FixedRunIdGenerator(),
    )
    result = processor.execute(
        ProcessAndPersistCommercialEventCommand(
            event=commercial_event(),
            evaluation_context=context(),
            rules_engine_version="rules-bootstrap",
        )
    )

    assert isinstance(processor, ProcessAndPersistCommercialEventUseCase)
    assert result.processing_run_id == "run-bootstrap"
    assert result.executed_phases == tuple(
        phase.value for phase in CommercialEventPhase
    )
    assert result.ledger_entry_id is None

    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        assert unit_of_work.events.get_by_id("event-bootstrap") == commercial_event()
        run = unit_of_work.processing_runs.get_by_id("run-bootstrap")
        assert run is not None
        assert run.final_status == "not_evaluable"
        assert len(run.phase_results) == len(CommercialEventPhase)
        assert unit_of_work.ledger.find_credit_by_event_id("event-bootstrap") is None

    engine.dispose()


def test_bootstrap_is_outside_application_package() -> None:
    assert build_transactional_processor.__module__ == "supervisor_ai.bootstrap"


def test_build_csv_import_service_reuses_complete_composition(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'csv-bootstrap.sqlite3'}"
    service = build_csv_import_service(database_url)

    assert isinstance(service, CsvImportService)
    assert service.__class__.__module__.startswith(
        "supervisor_ai.infrastructure.importing"
    )


def test_build_financial_snapshot_service_uses_application_query(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'snapshot-bootstrap.sqlite3'}"
    service = build_financial_snapshot_service(database_url)
    assert isinstance(service, GetFinancialSnapshotUseCase)
