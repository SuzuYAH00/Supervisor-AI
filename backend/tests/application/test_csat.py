from datetime import UTC, date, datetime
from decimal import Decimal
from types import TracebackType

import pytest

from supervisor_ai.application import (
    CsatEvaluation,
    CsatEvaluationConflict,
    CsatFilters,
    CsatSummaryGroupRecord,
    CsatSummaryRecord,
)
from supervisor_ai.application.use_cases import (
    CsatEvaluationInput,
    GetCsatEvaluationsUseCase,
    GetCsatSummaryUseCase,
    ImportCsatEvaluationsCommand,
    ImportCsatEvaluationsUseCase,
)

NOW = datetime(2026, 7, 20, 15, tzinfo=UTC)


def csat_input(score: str = "10") -> CsatEvaluationInput:
    return CsatEvaluationInput(
        evaluation_id="csat-1",
        external_reference="external-1",
        source="mkbot-export",
        collaborator_id="collaborator-1",
        channel="whatsapp",
        score=Decimal(score),
        evaluated_at=NOW,
    )


class FakeCsatRepository:
    def __init__(self) -> None:
        self.items: dict[str, CsatEvaluation] = {}
        self.search_result: tuple[CsatEvaluation, ...] = ()
        self.summary_result = CsatSummaryRecord(0, Decimal("0"), (), ())
        self.search_arguments: dict[str, object] = {}

    def add(self, evaluation: CsatEvaluation) -> None:
        self.items[evaluation.id] = evaluation

    def get_by_id(self, evaluation_id: str) -> CsatEvaluation | None:
        return self.items.get(evaluation_id)

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> CsatEvaluation | None:
        return next(
            (
                item
                for item in self.items.values()
                if item.source == source
                and item.external_reference == external_reference
            ),
            None,
        )

    def search(self, **filters: object) -> tuple[CsatEvaluation, ...]:
        self.search_arguments = filters
        return self.search_result

    def summarize(self, **filters: object) -> CsatSummaryRecord:
        self.search_arguments = filters
        return self.summary_result


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.csat = FakeCsatRepository()
        self.commit_calls = 0
        self.rollback_calls = 0
        self.closed = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        if exc_type is not None:
            self.rollback_calls += 1
        self.closed = True

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


def test_import_is_idempotent_and_conflicts_on_changed_facts() -> None:
    unit_of_work = FakeUnitOfWork()
    service = ImportCsatEvaluationsUseCase(lambda: unit_of_work, lambda: NOW)
    command = ImportCsatEvaluationsCommand((csat_input(),))

    first = service.execute(command)
    second = service.execute(command)

    assert first.created_count == 1
    assert second.created_count == 0
    assert second.already_existing_count == 1
    assert unit_of_work.commit_calls == 2
    assert unit_of_work.closed
    with pytest.raises(CsatEvaluationConflict):
        service.execute(ImportCsatEvaluationsCommand((csat_input("9"),)))
    assert unit_of_work.rollback_calls == 1


def test_query_filters_are_validated_and_reads_do_not_commit() -> None:
    with pytest.raises(ValueError):
        CsatFilters(start_date=date(2026, 8, 1), end_date=date(2026, 7, 1))
    with pytest.raises(ValueError):
        CsatFilters(source=" ")

    unit_of_work = FakeUnitOfWork()
    persisted = CsatEvaluation(
        id="csat-1",
        external_reference="external-1",
        source="mkbot-export",
        collaborator_id="collaborator-1",
        channel="whatsapp",
        score=Decimal("9.5"),
        evaluated_at=NOW,
        created_at=NOW,
    )
    unit_of_work.csat.search_result = (persisted,)
    query = CsatFilters(collaborator_id="collaborator-1", channel="whatsapp")
    result = GetCsatEvaluationsUseCase(lambda: unit_of_work).execute(query)

    assert result.evaluation_count == 1
    assert result.items[0].score == Decimal("9.5")
    assert unit_of_work.csat.search_arguments["collaborator_id"] == "collaborator-1"
    assert unit_of_work.commit_calls == 0
    assert unit_of_work.closed


def test_summary_computes_only_arithmetic_averages() -> None:
    unit_of_work = FakeUnitOfWork()
    unit_of_work.csat.summary_result = CsatSummaryRecord(
        evaluation_count=2,
        score_total=Decimal("18"),
        by_collaborator=(
            CsatSummaryGroupRecord("collaborator-1", 2, Decimal("18")),
        ),
        by_channel=(CsatSummaryGroupRecord("whatsapp", 2, Decimal("18")),),
    )

    result = GetCsatSummaryUseCase(lambda: unit_of_work).execute(CsatFilters())

    assert result.score_average == Decimal("9")
    assert result.by_collaborator[0].score_average == Decimal("9")
    assert result.by_channel[0].score_average == Decimal("9")
    assert unit_of_work.commit_calls == 0
