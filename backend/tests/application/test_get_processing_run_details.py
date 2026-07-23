from dataclasses import fields, replace
from types import TracebackType

import pytest

from supervisor_ai.application import ProcessingRunNotFound
from supervisor_ai.application.use_cases import (
    GetProcessingRunDetailsQuery,
    GetProcessingRunDetailsUseCase,
)
from tests.persistence.factories import commercial_event, processing_run


class RunRepositoryFake:
    def __init__(self, run=None, error=None, *, missing: bool = False) -> None:
        self.run = None if missing else (run or processing_run("run-1"))
        self.error = error
        self.received_id = None

    def get_by_id(self, run_id: str):
        self.received_id = run_id
        if self.error is not None:
            raise self.error
        return self.run


class EventRepositoryFake:
    def __init__(self, event=None) -> None:
        self.event = event or commercial_event()
        self.received_id = None

    def get_by_id(self, event_id: str):
        self.received_id = event_id
        return self.event


class UnitOfWorkFake:
    def __init__(self, runs: RunRepositoryFake, events: EventRepositoryFake) -> None:
        self.processing_runs = runs
        self.events = events
        self.closed = False
        self.rolled_back = False
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        self.closed = True
        self.rolled_back = exc_type is not None

    def commit(self) -> None:
        self.commits += 1


def test_existing_run_projects_allowlisted_fields_and_preserves_phase_order() -> None:
    run = replace(
        processing_run("run-1"),
        phase_results=[
            {
                "phase": "contract_facts",
                "status": "completed",
                "can_continue": True,
                "warnings": ["not-public"],
                "audit_references": ["internal-reference"],
                "output": {"secret": "never"},
            },
            {
                "phase": "payment_validation",
                "status": "not_evaluable",
                "can_continue": False,
            },
        ],
        warnings=["Traceback password"],
        audit_references=[{"raw_payload": "secret"}],
    )
    runs = RunRepositoryFake(run)
    events = EventRepositoryFake()
    unit_of_work = UnitOfWorkFake(runs, events)
    result = GetProcessingRunDetailsUseCase(lambda: unit_of_work).execute(
        GetProcessingRunDetailsQuery("run-1")
    )
    assert result.processing_run.processing_run_id == "run-1"
    assert result.commercial_event.event_id == "event-1"
    projected = [
        (phase.phase, phase.status, phase.can_continue) for phase in result.phases
    ]
    assert projected == [
        ("contract_facts", "completed", True),
        ("payment_validation", "not_evaluable", False),
    ]
    assert {field.name for field in fields(result.phases[0])} == {
        "phase",
        "status",
        "can_continue",
    }
    event_fields = {field.name for field in fields(result.commercial_event)}
    assert "raw_payload" not in event_fields
    assert runs.received_id == "run-1"
    assert events.received_id == "event-1"
    assert unit_of_work.closed and unit_of_work.commits == 0


def test_run_without_phases_returns_empty_collection() -> None:
    runs = RunRepositoryFake(replace(processing_run("run-1"), phase_results=[]))
    result = GetProcessingRunDetailsUseCase(
        lambda: UnitOfWorkFake(runs, EventRepositoryFake())
    ).execute(GetProcessingRunDetailsQuery("run-1"))
    assert result.phases == ()


def test_missing_run_stops_before_event_lookup() -> None:
    runs = RunRepositoryFake(missing=True)
    events = EventRepositoryFake()
    unit_of_work = UnitOfWorkFake(runs, events)
    with pytest.raises(ProcessingRunNotFound):
        GetProcessingRunDetailsUseCase(lambda: unit_of_work).execute(
            GetProcessingRunDetailsQuery("missing")
        )
    assert events.received_id is None
    assert unit_of_work.closed and unit_of_work.rolled_back


@pytest.mark.parametrize("run_id", ["", "   ", "x" * 129])
def test_query_rejects_invalid_identifier(run_id: str) -> None:
    with pytest.raises(ValueError):
        GetProcessingRunDetailsQuery(run_id)


def test_unexpected_failure_rolls_back_without_commit() -> None:
    unit_of_work = UnitOfWorkFake(
        RunRepositoryFake(error=RuntimeError("database failed")),
        EventRepositoryFake(),
    )
    with pytest.raises(RuntimeError):
        GetProcessingRunDetailsUseCase(lambda: unit_of_work).execute(
            GetProcessingRunDetailsQuery("run-1")
        )
    assert unit_of_work.closed and unit_of_work.rolled_back
    assert unit_of_work.commits == 0
