from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from supervisor_ai.application.errors import CsatEvaluationConflict
from supervisor_ai.application.persistence import CsatEvaluation
from supervisor_ai.application.ports import Clock, UnitOfWork, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class CsatEvaluationInput:
    evaluation_id: str
    external_reference: str
    source: str
    collaborator_id: str
    channel: str | None
    score: Decimal
    evaluated_at: datetime

    def __post_init__(self) -> None:
        CsatEvaluation(
            id=self.evaluation_id,
            external_reference=self.external_reference,
            source=self.source,
            collaborator_id=self.collaborator_id,
            channel=self.channel,
            score=self.score,
            evaluated_at=self.evaluated_at,
            created_at=self.evaluated_at,
        )


@dataclass(frozen=True, slots=True)
class ImportCsatEvaluationsCommand:
    evaluations: tuple[CsatEvaluationInput, ...]


@dataclass(frozen=True, slots=True)
class ImportCsatEvaluationsResult:
    received_count: int
    created_count: int
    already_existing_count: int
    evaluation_ids: tuple[str, ...]


class ImportCsatEvaluationsUseCase:
    def __init__(
        self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(
        self, command: ImportCsatEvaluationsCommand
    ) -> ImportCsatEvaluationsResult:
        created_at = self._clock()
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("clock must return timezone-aware datetimes")
        evaluations = tuple(
            CsatEvaluation(
                id=item.evaluation_id,
                external_reference=item.external_reference,
                source=item.source,
                collaborator_id=item.collaborator_id,
                channel=item.channel,
                score=item.score,
                evaluated_at=item.evaluated_at,
                created_at=created_at,
            )
            for item in command.evaluations
        )
        created_count = 0
        with self._unit_of_work_factory() as unit_of_work:
            for evaluation in evaluations:
                if self._ensure_evaluation(unit_of_work, evaluation):
                    created_count += 1
            unit_of_work.commit()
        return ImportCsatEvaluationsResult(
            received_count=len(evaluations),
            created_count=created_count,
            already_existing_count=len(evaluations) - created_count,
            evaluation_ids=tuple(item.id for item in evaluations),
        )

    @staticmethod
    def _ensure_evaluation(
        unit_of_work: UnitOfWork, evaluation: CsatEvaluation
    ) -> bool:
        by_reference = unit_of_work.csat.get_by_source_reference(
            source=evaluation.source,
            external_reference=evaluation.external_reference,
        )
        by_id = unit_of_work.csat.get_by_id(evaluation.id)
        existing = by_reference or by_id
        if existing is None:
            unit_of_work.csat.add(evaluation)
            return True
        if not _same_evaluation(existing, evaluation):
            raise CsatEvaluationConflict(
                "CSAT evaluation identity differs from persisted facts"
            )
        return False


def _same_evaluation(first: CsatEvaluation, second: CsatEvaluation) -> bool:
    return all(
        (
            first.id == second.id,
            first.external_reference == second.external_reference,
            first.source == second.source,
            first.collaborator_id == second.collaborator_id,
            first.channel == second.channel,
            first.score == second.score,
            first.evaluated_at == second.evaluated_at,
        )
    )
