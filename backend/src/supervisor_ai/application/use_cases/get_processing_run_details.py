from dataclasses import dataclass
from datetime import datetime

from supervisor_ai.application.errors import ProcessingRunNotFound
from supervisor_ai.application.persistence import JsonValue, ProcessingRun
from supervisor_ai.application.ports import UnitOfWorkFactory

MAX_PROCESSING_RUN_ID_LENGTH = 128


@dataclass(frozen=True, slots=True)
class GetProcessingRunDetailsQuery:
    processing_run_id: str

    def __post_init__(self) -> None:
        if not self.processing_run_id.strip():
            raise ValueError("processing_run_id must not be blank")
        if len(self.processing_run_id) > MAX_PROCESSING_RUN_ID_LENGTH:
            raise ValueError(
                "processing_run_id must not exceed "
                f"{MAX_PROCESSING_RUN_ID_LENGTH} characters"
            )


@dataclass(frozen=True, slots=True)
class ProcessingRunDetails:
    processing_run_id: str
    event_id: str
    final_status: str
    started_at: datetime
    completed_at: datetime
    rules_engine_version: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProcessingRunCommercialEvent:
    event_id: str
    external_reference: str
    source: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ProcessingRunPhaseDetails:
    phase: str
    status: str
    can_continue: bool


@dataclass(frozen=True, slots=True)
class GetProcessingRunDetailsResult:
    processing_run: ProcessingRunDetails
    commercial_event: ProcessingRunCommercialEvent
    phases: tuple[ProcessingRunPhaseDetails, ...]


class GetProcessingRunDetailsUseCase:
    """Projeta uma execução persistida por allowlist, sem reprocessamento."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, query: GetProcessingRunDetailsQuery
    ) -> GetProcessingRunDetailsResult:
        with self._unit_of_work_factory() as unit_of_work:
            run = unit_of_work.processing_runs.get_by_id(query.processing_run_id)
            if run is None:
                raise ProcessingRunNotFound(query.processing_run_id)
            event = unit_of_work.events.get_by_id(run.event_id)
            if event is None:
                raise RuntimeError("processing run references a missing event")
        return GetProcessingRunDetailsResult(
            processing_run=_run_details(run),
            commercial_event=ProcessingRunCommercialEvent(
                event_id=event.id,
                external_reference=event.external_reference,
                source=event.source,
                occurred_at=event.occurred_at,
            ),
            phases=tuple(_phase_details(item) for item in run.phase_results),
        )


def _run_details(run: ProcessingRun) -> ProcessingRunDetails:
    return ProcessingRunDetails(
        processing_run_id=run.id,
        event_id=run.event_id,
        final_status=run.final_status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        rules_engine_version=run.rules_engine_version,
        created_at=run.created_at,
    )


def _phase_details(value: JsonValue) -> ProcessingRunPhaseDetails:
    if not isinstance(value, dict):
        raise ValueError("persisted phase result must be an object")
    phase = value.get("phase")
    status = value.get("status")
    can_continue = value.get("can_continue")
    if not isinstance(phase, str) or not phase:
        raise ValueError("persisted phase must have a phase")
    if not isinstance(status, str) or not status:
        raise ValueError("persisted phase must have a status")
    if type(can_continue) is not bool:
        raise ValueError("persisted phase must have can_continue")
    return ProcessingRunPhaseDetails(phase, status, can_continue)
