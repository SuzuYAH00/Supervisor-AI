from dataclasses import dataclass
from typing import Protocol

from supervisor_ai.application.use_cases import (
    ProcessAndPersistCommercialEventCommand,
    ProcessAndPersistCommercialEventResult,
)
from supervisor_ai.infrastructure.importing.mapper import JsonImportDocumentMapper
from supervisor_ai.infrastructure.importing.parser import parse_json_text
from supervisor_ai.infrastructure.importing.schema import JsonImportDocumentValidator


class TransactionalCommercialEventProcessor(Protocol):
    def execute(
        self, command: ProcessAndPersistCommercialEventCommand
    ) -> ProcessAndPersistCommercialEventResult: ...


@dataclass(frozen=True, slots=True)
class JsonImportResult:
    event_id: str
    processing_run_id: str
    final_status: str
    event_persisted: bool
    ledger_entry_id: str | None
    ledger_persisted: bool
    ledger_already_existed: bool
    warnings: tuple[str, ...]
    audit_references: tuple[str, ...]


class JsonCommercialEventImporter:
    def __init__(
        self,
        *,
        processor: TransactionalCommercialEventProcessor,
        validator: JsonImportDocumentValidator | None = None,
        mapper: JsonImportDocumentMapper | None = None,
    ) -> None:
        self._processor = processor
        self._validator = validator or JsonImportDocumentValidator()
        self._mapper = mapper or JsonImportDocumentMapper()

    def import_document(self, text: str) -> JsonImportResult:
        parsed = parse_json_text(text)
        document = self._validator.validate(parsed)
        command = self._mapper.map(document)
        result = self._processor.execute(command)
        return JsonImportResult(
            event_id=result.event_id,
            processing_run_id=result.processing_run_id,
            final_status=result.final_status,
            event_persisted=result.event_persisted,
            ledger_entry_id=result.ledger_entry_id,
            ledger_persisted=result.ledger_persisted,
            ledger_already_existed=result.ledger_already_existed,
            warnings=result.warnings,
            audit_references=result.audit_references,
        )
