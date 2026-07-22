from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from supervisor_ai.application import (
    Clock,
    CommercialEventConflict,
    LedgerConflict,
)
from supervisor_ai.infrastructure.importing.errors import ImportDocumentError


class ImportResult(Protocol):
    event_id: str
    processing_run_id: str
    final_status: str
    event_persisted: bool
    ledger_entry_id: str | None
    ledger_persisted: bool
    ledger_already_existed: bool
    warnings: tuple[str, ...]
    audit_references: tuple[str, ...]


class DocumentImporter[DocumentT](Protocol):
    def import_document(self, document: DocumentT) -> ImportResult: ...


class BatchDocumentStatus(StrEnum):
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    BUSINESS_CONFLICT = "business_conflict"
    TECHNICAL_ERROR = "technical_error"


@dataclass(frozen=True, slots=True)
class BatchDocument[DocumentT]:
    identifier: str
    document: DocumentT

    def __post_init__(self) -> None:
        if not self.identifier:
            raise ValueError("document identifier must not be empty")


@dataclass(frozen=True, slots=True)
class BatchDocumentResult:
    document_identifier: str
    processing_status: BatchDocumentStatus
    started_at: datetime
    completed_at: datetime
    execution_duration: timedelta
    processing_run_id: str | None = None
    commercial_event_id: str | None = None
    ledger_entry_id: str | None = None
    final_status: str | None = None
    event_persisted: bool = False
    ledger_persisted: bool = False
    ledger_already_existed: bool = False
    warnings: tuple[str, ...] = ()
    audit_references: tuple[str, ...] = ()
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        _require_aware(self.started_at, "started_at")
        _require_aware(self.completed_at, "completed_at")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if self.execution_duration != self.completed_at - self.started_at:
            raise ValueError("execution_duration must match document timestamps")
        if self.processing_status is BatchDocumentStatus.SUCCESS:
            if (
                self.processing_run_id is None
                or self.commercial_event_id is None
                or self.final_status is None
            ):
                raise ValueError("successful document must identify event and run")
            if self.error_type is not None or self.error_message is not None:
                raise ValueError("successful document cannot contain an error")
        elif self.error_type is None or self.error_message is None:
            raise ValueError("failed document must describe its error")


@dataclass(frozen=True, slots=True)
class BatchStatistics:
    total_documents: int
    successful_documents: int
    validation_errors: int
    business_conflicts: int
    technical_errors: int
    processing_runs_created: int
    ledger_entries_created: int

    @classmethod
    def from_results(
        cls, results: tuple[BatchDocumentResult, ...]
    ) -> "BatchStatistics":
        def count(status: BatchDocumentStatus) -> int:
            return sum(item.processing_status is status for item in results)

        successful = count(BatchDocumentStatus.SUCCESS)
        return cls(
            total_documents=len(results),
            successful_documents=successful,
            validation_errors=count(BatchDocumentStatus.VALIDATION_ERROR),
            business_conflicts=count(BatchDocumentStatus.BUSINESS_CONFLICT),
            technical_errors=count(BatchDocumentStatus.TECHNICAL_ERROR),
            processing_runs_created=successful,
            ledger_entries_created=sum(item.ledger_persisted for item in results),
        )


@dataclass(frozen=True, slots=True)
class BatchImportResult:
    started_at: datetime
    completed_at: datetime
    processing_duration: timedelta
    statistics: BatchStatistics
    ordered_results: tuple[BatchDocumentResult, ...]

    def __post_init__(self) -> None:
        _require_aware(self.started_at, "started_at")
        _require_aware(self.completed_at, "completed_at")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if self.processing_duration != self.completed_at - self.started_at:
            raise ValueError("processing_duration must match batch timestamps")
        if self.statistics != BatchStatistics.from_results(self.ordered_results):
            raise ValueError("statistics must match ordered results")


class BatchImportProcessor[DocumentT]:
    """Coordena imports independentes sem conhecer o formato dos documentos."""

    def __init__(
        self,
        *,
        importer: DocumentImporter[DocumentT],
        clock: Clock,
    ) -> None:
        self._importer = importer
        self._clock = clock

    def process(
        self, documents: Iterable[BatchDocument[DocumentT]]
    ) -> BatchImportResult:
        batch_started_at = self._aware_now()
        results = tuple(self._process_document(item) for item in documents)
        batch_completed_at = self._aware_now()
        return BatchImportResult(
            started_at=batch_started_at,
            completed_at=batch_completed_at,
            processing_duration=batch_completed_at - batch_started_at,
            statistics=BatchStatistics.from_results(results),
            ordered_results=results,
        )

    def _process_document(
        self, item: BatchDocument[DocumentT]
    ) -> BatchDocumentResult:
        started_at = self._aware_now()
        try:
            imported = self._importer.import_document(item.document)
        except ImportDocumentError as error:
            return self._failure(
                item.identifier,
                BatchDocumentStatus.VALIDATION_ERROR,
                started_at,
                error,
            )
        except (CommercialEventConflict, LedgerConflict) as error:
            return self._failure(
                item.identifier,
                BatchDocumentStatus.BUSINESS_CONFLICT,
                started_at,
                error,
            )
        except Exception as error:
            return self._failure(
                item.identifier,
                BatchDocumentStatus.TECHNICAL_ERROR,
                started_at,
                error,
            )

        completed_at = self._aware_now()
        return BatchDocumentResult(
            document_identifier=item.identifier,
            processing_status=BatchDocumentStatus.SUCCESS,
            started_at=started_at,
            completed_at=completed_at,
            execution_duration=completed_at - started_at,
            processing_run_id=imported.processing_run_id,
            commercial_event_id=imported.event_id,
            ledger_entry_id=imported.ledger_entry_id,
            final_status=imported.final_status,
            event_persisted=imported.event_persisted,
            ledger_persisted=imported.ledger_persisted,
            ledger_already_existed=imported.ledger_already_existed,
            warnings=imported.warnings,
            audit_references=imported.audit_references,
        )

    def _failure(
        self,
        identifier: str,
        status: BatchDocumentStatus,
        started_at: datetime,
        error: Exception,
    ) -> BatchDocumentResult:
        completed_at = self._aware_now()
        return BatchDocumentResult(
            document_identifier=identifier,
            processing_status=status,
            started_at=started_at,
            completed_at=completed_at,
            execution_duration=completed_at - started_at,
            error_type=type(error).__name__,
            error_message=str(error),
        )

    def _aware_now(self) -> datetime:
        value = self._clock()
        _require_aware(value, "clock result")
        return value


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
