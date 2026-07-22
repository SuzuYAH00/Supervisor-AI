from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from supervisor_ai.application import CommercialEventConflict, LedgerConflict
from supervisor_ai.infrastructure.importing import (
    BatchDocument,
    BatchDocumentResult,
    BatchDocumentStatus,
    BatchImportProcessor,
    BatchImportResult,
    BatchStatistics,
    ImportValidationError,
    JsonImportResult,
)

START = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)


class AdvancingClock:
    def __init__(self) -> None:
        self._calls = 0

    def __call__(self) -> datetime:
        value = START + timedelta(seconds=self._calls)
        self._calls += 1
        return value


class StubImporter:
    def __init__(self, outcomes: dict[str, JsonImportResult | Exception]) -> None:
        self.outcomes = outcomes
        self.calls: list[str] = []

    def import_document(self, document: str) -> JsonImportResult:
        self.calls.append(document)
        outcome = self.outcomes[document]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def imported(identifier: str, *, ledger_persisted: bool = False) -> JsonImportResult:
    return JsonImportResult(
        event_id=f"event-{identifier}",
        processing_run_id=f"run-{identifier}",
        final_status="posted" if ledger_persisted else "not_evaluable",
        event_persisted=True,
        ledger_entry_id=f"entry-{identifier}" if ledger_persisted else None,
        ledger_persisted=ledger_persisted,
        ledger_already_existed=False,
        warnings=(),
        audit_references=(),
    )


def result(
    identifier: str,
    status: BatchDocumentStatus = BatchDocumentStatus.SUCCESS,
) -> BatchDocumentResult:
    error = status is not BatchDocumentStatus.SUCCESS
    return BatchDocumentResult(
        document_identifier=identifier,
        processing_status=status,
        started_at=START,
        completed_at=START + timedelta(seconds=1),
        execution_duration=timedelta(seconds=1),
        processing_run_id=None if error else f"run-{identifier}",
        commercial_event_id=None if error else f"event-{identifier}",
        final_status=None if error else "not_evaluable",
        error_type="Failure" if error else None,
        error_message="failed" if error else None,
    )


def test_public_batch_contracts_are_immutable_and_aggregate_results() -> None:
    results = (
        result("one"),
        result("two", BatchDocumentStatus.VALIDATION_ERROR),
        result("three", BatchDocumentStatus.BUSINESS_CONFLICT),
        result("four", BatchDocumentStatus.TECHNICAL_ERROR),
    )
    statistics = BatchStatistics.from_results(results)
    batch = BatchImportResult(
        started_at=START,
        completed_at=START + timedelta(seconds=4),
        processing_duration=timedelta(seconds=4),
        statistics=statistics,
        ordered_results=results,
    )

    assert statistics == BatchStatistics(4, 1, 1, 1, 1, 1, 0)
    assert batch.ordered_results == results
    with pytest.raises(FrozenInstanceError):
        batch.statistics = BatchStatistics(0, 0, 0, 0, 0, 0, 0)


def test_batch_document_requires_a_stable_identifier() -> None:
    with pytest.raises(ValueError, match="identifier"):
        BatchDocument(identifier="", document="payload")


def test_batch_result_rejects_statistics_that_do_not_match_results() -> None:
    with pytest.raises(ValueError, match="statistics"):
        BatchImportResult(
            started_at=START,
            completed_at=START,
            processing_duration=timedelta(),
            statistics=BatchStatistics(0, 0, 0, 0, 0, 0, 0),
            ordered_results=(result("one"),),
        )


def test_processor_continues_in_order_across_all_error_categories() -> None:
    outcomes: dict[str, JsonImportResult | Exception] = {
        "one": imported("one", ledger_persisted=True),
        "two": ImportValidationError("evaluation.subject_id: required"),
        "three": imported("three"),
        "four": LedgerConflict("credit differs"),
        "five": imported("five", ledger_persisted=True),
        "six": CommercialEventConflict("external reference reused"),
        "seven": RuntimeError("database unavailable"),
    }
    importer = StubImporter(outcomes)
    processor = BatchImportProcessor(importer=importer, clock=AdvancingClock())
    documents = tuple(
        BatchDocument(identifier=f"document-{name}", document=name)
        for name in outcomes
    )

    batch = processor.process(documents)

    assert importer.calls == list(outcomes)
    assert tuple(item.document_identifier for item in batch.ordered_results) == tuple(
        f"document-{name}" for name in outcomes
    )
    assert tuple(item.processing_status for item in batch.ordered_results) == (
        BatchDocumentStatus.SUCCESS,
        BatchDocumentStatus.VALIDATION_ERROR,
        BatchDocumentStatus.SUCCESS,
        BatchDocumentStatus.BUSINESS_CONFLICT,
        BatchDocumentStatus.SUCCESS,
        BatchDocumentStatus.BUSINESS_CONFLICT,
        BatchDocumentStatus.TECHNICAL_ERROR,
    )
    assert batch.statistics == BatchStatistics(7, 3, 1, 2, 1, 3, 2)
    assert batch.ordered_results[3].error_type == "LedgerConflict"
    assert batch.ordered_results[5].error_type == "CommercialEventConflict"
    assert batch.ordered_results[6].error_message == "database unavailable"
    assert batch.processing_duration == timedelta(seconds=15)


def test_all_successful_documents_create_individual_results() -> None:
    importer = StubImporter({"one": imported("one"), "two": imported("two")})
    processor = BatchImportProcessor(importer=importer, clock=AdvancingClock())

    batch = processor.process(
        (
            BatchDocument("first", "one"),
            BatchDocument("second", "two"),
        )
    )

    assert batch.statistics == BatchStatistics(2, 2, 0, 0, 0, 2, 0)
    assert batch.ordered_results[0].processing_run_id == "run-one"
    assert batch.ordered_results[1].commercial_event_id == "event-two"
