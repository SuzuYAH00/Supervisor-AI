from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from supervisor_ai.application.errors import OperationalCollaboratorProfileNotFound
from supervisor_ai.application.ports import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class GetMonthlyCsatFactsQuery:
    competence_month: date
    collaborator_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.competence_month.day != 1:
            raise ValueError("competence_month must be the first day of a month")
        if len(self.collaborator_ids) != len(set(self.collaborator_ids)):
            raise ValueError("collaborator_ids must not contain duplicates")
        if any(not value.strip() for value in self.collaborator_ids):
            raise ValueError("collaborator_ids must not contain blank values")


@dataclass(frozen=True, slots=True)
class MonthlyCsatFact:
    collaborator_id: str
    reference_month: date
    eligible_contact_count: int
    valid_response_count: int
    response_rate: Decimal | None
    raw_average: Decimal | None
    competitive_score: Decimal | None


@dataclass(frozen=True, slots=True)
class GetMonthlyCsatFactsResult:
    competence_month: date
    items: tuple[MonthlyCsatFact, ...]


class GetMonthlyCsatFactsUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: GetMonthlyCsatFactsQuery) -> GetMonthlyCsatFactsResult:
        with self._unit_of_work_factory() as unit_of_work:
            profiles = unit_of_work.operational_collaborators.get_by_ids(
                query.collaborator_ids
            )
            contacts = unit_of_work.csat_contacts.search_competence(
                competence_month=query.competence_month,
                collaborator_ids=query.collaborator_ids,
            )
        profile_by_id = {item.collaborator_id: item for item in profiles}
        missing = set(query.collaborator_ids) - set(profile_by_id)
        if missing:
            raise OperationalCollaboratorProfileNotFound(
                f"operational profiles are missing for: {', '.join(sorted(missing))}"
            )
        items = []
        for collaborator_id in query.collaborator_ids:
            channel = profile_by_id[collaborator_id].competitive_channel
            matching = tuple(
                item
                for item in contacts
                if item.collaborator_id == collaborator_id
                and item.source_channel is channel
            )
            scores = tuple(item.score for item in matching if item.score is not None)
            contact_count = len(matching)
            response_count = len(scores)
            raw_average = (
                None
                if not scores
                else sum(scores, start=Decimal("0")) / Decimal(response_count)
            )
            items.append(
                MonthlyCsatFact(
                    collaborator_id=collaborator_id,
                    reference_month=query.competence_month,
                    eligible_contact_count=contact_count,
                    valid_response_count=response_count,
                    response_rate=(
                        None
                        if contact_count == 0
                        else Decimal(response_count) / Decimal(contact_count)
                    ),
                    raw_average=raw_average,
                    competitive_score=(
                        None if raw_average is None else raw_average * Decimal("2")
                    ),
                )
            )
        return GetMonthlyCsatFactsResult(query.competence_month, tuple(items))
