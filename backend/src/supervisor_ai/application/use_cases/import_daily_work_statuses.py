from dataclasses import dataclass
from datetime import date, datetime

from supervisor_ai.application.errors import (
    CollaboratorExternalIdentityNotFound,
    DailyWorkStatusConflict,
)
from supervisor_ai.application.persistence import DailyWorkStatusFact
from supervisor_ai.application.ports import Clock, UnitOfWork, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class DailyWorkStatusInput:
    fact_id: str
    external_identity: str
    work_date: date
    competence_month: date
    raw_code: str
    source: str
    external_reference: str
    source_sheet: str
    source_cell: str


@dataclass(frozen=True, slots=True)
class ImportDailyWorkStatusesCommand:
    facts: tuple[DailyWorkStatusInput, ...]


@dataclass(frozen=True, slots=True)
class ImportDailyWorkStatusesResult:
    received_count: int
    created_count: int
    already_existing_count: int
    fact_ids: tuple[str, ...]


class ImportDailyWorkStatusesUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(
        self, command: ImportDailyWorkStatusesCommand
    ) -> ImportDailyWorkStatusesResult:
        created_at = self._clock()
        _require_aware(created_at)
        created_count = 0
        fact_ids: list[str] = []
        with self._unit_of_work_factory() as unit_of_work:
            for item in command.facts:
                identity = (
                    unit_of_work.collaborator_external_identities
                    .get_by_source_identity(
                        source=item.source,
                        external_identity=item.external_identity,
                    )
                )
                if identity is None:
                    raise CollaboratorExternalIdentityNotFound(
                        f"unmapped external identity at "
                        f"{item.source_sheet}!A{_cell_row(item.source_cell)}"
                    )
                fact = _to_fact(item, identity.collaborator_id, created_at)
                fact_ids.append(fact.id)
                if self._ensure_fact(unit_of_work, fact):
                    created_count += 1
            unit_of_work.commit()
        return ImportDailyWorkStatusesResult(
            received_count=len(command.facts),
            created_count=created_count,
            already_existing_count=len(command.facts) - created_count,
            fact_ids=tuple(fact_ids),
        )

    @staticmethod
    def _ensure_fact(unit_of_work: UnitOfWork, fact: DailyWorkStatusFact) -> bool:
        by_reference = unit_of_work.daily_work_statuses.get_by_source_reference(
            source=fact.source,
            external_reference=fact.external_reference,
        )
        by_date = unit_of_work.daily_work_statuses.get_by_collaborator_date(
            collaborator_id=fact.collaborator_id,
            work_date=fact.work_date,
        )
        by_id = unit_of_work.daily_work_statuses.get_by_id(fact.id)
        existing = by_reference or by_date or by_id
        if existing is None:
            unit_of_work.daily_work_statuses.add(fact)
            return True
        if not _same_fact(existing, fact):
            raise DailyWorkStatusConflict(
                "daily work status identity differs from persisted facts"
            )
        return False


def _to_fact(
    item: DailyWorkStatusInput,
    collaborator_id: str,
    created_at: datetime,
) -> DailyWorkStatusFact:
    return DailyWorkStatusFact(
        id=item.fact_id,
        collaborator_id=collaborator_id,
        work_date=item.work_date,
        competence_month=item.competence_month,
        raw_code=item.raw_code,
        source=item.source,
        external_reference=item.external_reference,
        source_sheet=item.source_sheet,
        source_cell=item.source_cell,
        created_at=created_at,
    )


def _same_fact(first: DailyWorkStatusFact, second: DailyWorkStatusFact) -> bool:
    return all(
        (
            first.id == second.id,
            first.collaborator_id == second.collaborator_id,
            first.work_date == second.work_date,
            first.competence_month == second.competence_month,
            first.raw_code == second.raw_code,
            first.source == second.source,
            first.external_reference == second.external_reference,
            first.source_sheet == second.source_sheet,
            first.source_cell == second.source_cell,
        )
    )


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return timezone-aware datetimes")


def _cell_row(cell_reference: str) -> str:
    return "".join(character for character in cell_reference if character.isdigit())
