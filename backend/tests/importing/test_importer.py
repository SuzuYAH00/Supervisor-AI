from dataclasses import dataclass, field

import pytest

from supervisor_ai.application import CommercialEventConflict, LedgerConflict
from supervisor_ai.application.use_cases import (
    ProcessAndPersistCommercialEventCommand,
    ProcessAndPersistCommercialEventResult,
)
from supervisor_ai.infrastructure.importing import (
    ImportValidationError,
    JsonCommercialEventImporter,
)
from tests.importing.factories import document, json_text


@dataclass
class ProcessorSpy:
    error: Exception | None = None
    commands: list[ProcessAndPersistCommercialEventCommand] = field(
        default_factory=list
    )

    def execute(
        self, command: ProcessAndPersistCommercialEventCommand
    ) -> ProcessAndPersistCommercialEventResult:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        return ProcessAndPersistCommercialEventResult(
            event_id=command.event.id,
            processing_run_id="run-json-1",
            final_status="not_evaluable",
            event_persisted=True,
            ledger_entry_id=None,
            ledger_persisted=False,
            ledger_already_existed=False,
            executed_phases=("contract_facts",),
            warnings=("warning-1",),
            audit_references=("audit-1",),
        )


def test_calls_processor_once_and_returns_auditable_result() -> None:
    processor = ProcessorSpy()
    importer = JsonCommercialEventImporter(processor=processor)

    result = importer.import_document(json_text())

    assert len(processor.commands) == 1
    assert processor.commands[0].event.id == "event-json-1"
    assert result.event_id == "event-json-1"
    assert result.processing_run_id == "run-json-1"
    assert result.final_status == "not_evaluable"
    assert result.event_persisted is True
    assert result.ledger_entry_id is None
    assert result.ledger_persisted is False
    assert result.warnings == ("warning-1",)
    assert result.audit_references == ("audit-1",)


def test_does_not_call_processor_when_validation_fails() -> None:
    processor = ProcessorSpy()
    importer = JsonCommercialEventImporter(processor=processor)
    value = document()
    value["rules_engine_version"] = ""

    with pytest.raises(ImportValidationError):
        importer.import_document(json_text(value))

    assert processor.commands == []


@pytest.mark.parametrize(
    "error",
    [
        CommercialEventConflict("event conflict"),
        LedgerConflict("ledger conflict"),
        RuntimeError("unexpected processor failure"),
    ],
)
def test_propagates_processor_errors(error: Exception) -> None:
    importer = JsonCommercialEventImporter(processor=ProcessorSpy(error=error))
    with pytest.raises(type(error), match=str(error)):
        importer.import_document(json_text())
