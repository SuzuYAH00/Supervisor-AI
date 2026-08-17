from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from supervisor_ai.application.errors import OperationalCollaboratorProfileNotFound
from supervisor_ai.application.persistence import (
    DailyWorkStatusFact,
    OperationalCollaboratorProfile,
)
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.rules_engine import (
    CHAT_MINIMUM_RESPONSE_RATE,
    MINIMUM_WORKED_DAYS,
    PHONE_COMPETITIVE_MAXIMUM_SCORE,
    PHONE_MINIMUM_RESPONSE_RATE,
    CsatCompetitiveChannel,
    CsatVariableCompensationFacts,
    MonthlyPresenceResult,
    MonthlyVariableCompensationEvaluator,
    MonthlyVariableCompensationInput,
    MonthlyVariableCompensationResult,
    PresenceDay,
    RecurrenceVariableCompensationFacts,
    VariableCompensationCompetence,
    summarize_monthly_presence,
)


@dataclass(frozen=True, slots=True)
class CsatCompetitiveFact:
    collaborator_id: str
    reference_month: date
    competitive_score: Decimal | None
    response_rate: Decimal | None

    def __post_init__(self) -> None:
        _validate_identity_and_month(self.collaborator_id, self.reference_month)
        _validate_decimal(self.competitive_score, "competitive_score")
        _validate_rate(self.response_rate, "response_rate")


@dataclass(frozen=True, slots=True)
class RecurrenceCompetitiveFact:
    collaborator_id: str
    cohort_month: date
    recurrence_rate: Decimal | None

    def __post_init__(self) -> None:
        _validate_identity_and_month(self.collaborator_id, self.cohort_month)
        _validate_rate(self.recurrence_rate, "recurrence_rate")


@dataclass(frozen=True, slots=True)
class MonthlyDelayCountFact:
    collaborator_id: str
    reference_month: date
    delay_count: int

    def __post_init__(self) -> None:
        _validate_identity_and_month(self.collaborator_id, self.reference_month)
        if self.delay_count < 0:
            raise ValueError("delay_count must not be negative")


@dataclass(frozen=True, slots=True)
class CalculateMonthlyVariableCompensationCommand:
    competence_month: date
    collaborator_ids: tuple[str, ...]
    csat_facts: tuple[CsatCompetitiveFact, ...]
    recurrence_facts: tuple[RecurrenceCompetitiveFact, ...]
    delay_facts: tuple[MonthlyDelayCountFact, ...]

    def __post_init__(self) -> None:
        if self.competence_month.day != 1:
            raise ValueError("competence_month must be the first day of a month")
        _validate_unique_identities(self.collaborator_ids, "collaborator_ids")
        if any(not value.strip() for value in self.collaborator_ids):
            raise ValueError("collaborator_ids must not contain blank values")
        _validate_fact_set(self.csat_facts, self.collaborator_ids, "CSAT")
        _validate_fact_set(
            self.recurrence_facts, self.collaborator_ids, "recurrence"
        )
        _validate_fact_set(self.delay_facts, self.collaborator_ids, "delay")
        previous_month = _previous_month(self.competence_month)
        if any(
            item.reference_month != self.competence_month
            for item in self.csat_facts
        ):
            raise ValueError("CSAT facts must match competence_month")
        if any(
            item.cohort_month != previous_month for item in self.recurrence_facts
        ):
            raise ValueError("recurrence facts must match the previous month")
        if any(
            item.reference_month != self.competence_month
            for item in self.delay_facts
        ):
            raise ValueError("delay facts must match competence_month")


@dataclass(frozen=True, slots=True)
class CalculateMonthlyVariableCompensationResult:
    competence_month: date
    items: tuple[MonthlyVariableCompensationResult, ...]


class CalculateMonthlyVariableCompensationUseCase:
    """Compõe fatos mensais resolvidos sem conhecer planilha ou ORM."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        evaluator: MonthlyVariableCompensationEvaluator,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._evaluator = evaluator

    def execute(
        self, command: CalculateMonthlyVariableCompensationCommand
    ) -> CalculateMonthlyVariableCompensationResult:
        previous_month = _previous_month(command.competence_month)
        with self._unit_of_work_factory() as unit_of_work:
            profiles = unit_of_work.operational_collaborators.get_by_ids(
                command.collaborator_ids
            )
            current_presence = unit_of_work.daily_work_statuses.search_competence(
                competence_month=command.competence_month,
                collaborator_ids=command.collaborator_ids,
            )
            previous_presence = unit_of_work.daily_work_statuses.search_competence(
                competence_month=previous_month,
                collaborator_ids=command.collaborator_ids,
            )
        profile_by_id = {item.collaborator_id: item for item in profiles}
        missing = set(command.collaborator_ids) - set(profile_by_id)
        if missing:
            raise OperationalCollaboratorProfileNotFound(
                f"operational profiles are missing for: {', '.join(sorted(missing))}"
            )
        current_by_id = _presence_by_collaborator(
            current_presence, command.collaborator_ids
        )
        previous_by_id = _presence_by_collaborator(
            previous_presence, command.collaborator_ids
        )
        csat_by_id = {item.collaborator_id: item for item in command.csat_facts}
        recurrence_by_id = {
            item.collaborator_id: item for item in command.recurrence_facts
        }
        delay_by_id = {item.collaborator_id: item for item in command.delay_facts}
        csat_averages = _csat_averages(
            command.collaborator_ids,
            profile_by_id,
            current_by_id,
            csat_by_id,
        )
        recurrence_average = _recurrence_average(
            command.collaborator_ids,
            previous_by_id,
            recurrence_by_id,
        )
        competence = VariableCompensationCompetence(
            competence_month=command.competence_month,
            csat_reference_month=command.competence_month,
            recurrence_cohort_month=previous_month,
            attendance_reference_month=command.competence_month,
        )
        results = tuple(
            self._evaluator.evaluate(
                MonthlyVariableCompensationInput(
                    collaborator_id=collaborator_id,
                    competence=competence,
                    csat=_csat_input(
                        collaborator_id,
                        profile_by_id,
                        current_by_id,
                        csat_by_id,
                        csat_averages,
                    ),
                    recurrence=RecurrenceVariableCompensationFacts(
                        is_eligible=(
                            previous_by_id[collaborator_id]
                            .meets_minimum_worked_days
                        ),
                        operator_rate=(
                            recurrence_by_id[collaborator_id].recurrence_rate
                        ),
                        population_average_rate=recurrence_average,
                    ),
                    delay_count=delay_by_id[collaborator_id].delay_count,
                    absence_days=(
                        current_by_id[collaborator_id].penalizable_absence_days
                    ),
                )
            )
            for collaborator_id in command.collaborator_ids
        )
        return CalculateMonthlyVariableCompensationResult(
            competence_month=command.competence_month,
            items=results,
        )


def _csat_input(
    collaborator_id: str,
    profiles: dict[str, OperationalCollaboratorProfile],
    presence: dict[str, MonthlyPresenceResult],
    facts: dict[str, CsatCompetitiveFact],
    averages: dict[CsatCompetitiveChannel, Decimal | None],
) -> CsatVariableCompensationFacts:
    channel = profiles[collaborator_id].competitive_channel
    fact = facts[collaborator_id]
    return CsatVariableCompensationFacts(
        worked_days=presence[collaborator_id].worked_days,
        channel=channel,
        response_rate=fact.response_rate,
        operator_score=fact.competitive_score,
        channel_average=averages[channel],
        channel_maximum_score=(
            PHONE_COMPETITIVE_MAXIMUM_SCORE
            if channel is CsatCompetitiveChannel.PHONE
            else None
        ),
    )


def _csat_averages(
    collaborator_ids: tuple[str, ...],
    profiles: dict[str, OperationalCollaboratorProfile],
    presence: dict[str, MonthlyPresenceResult],
    facts: dict[str, CsatCompetitiveFact],
) -> dict[CsatCompetitiveChannel, Decimal | None]:
    scores: dict[CsatCompetitiveChannel, list[Decimal]] = {
        CsatCompetitiveChannel.CHAT: [],
        CsatCompetitiveChannel.PHONE: [],
    }
    for collaborator_id in collaborator_ids:
        channel = profiles[collaborator_id].competitive_channel
        fact = facts[collaborator_id]
        minimum_response = (
            CHAT_MINIMUM_RESPONSE_RATE
            if channel is CsatCompetitiveChannel.CHAT
            else PHONE_MINIMUM_RESPONSE_RATE
        )
        if (
            presence[collaborator_id].worked_days >= MINIMUM_WORKED_DAYS
            and fact.response_rate is not None
            and fact.response_rate >= minimum_response
            and fact.competitive_score is not None
        ):
            scores[channel].append(fact.competitive_score)
    return {
        channel: (
            None
            if not values
            else sum(values, start=Decimal("0")) / Decimal(len(values))
        )
        for channel, values in scores.items()
    }


def _recurrence_average(
    collaborator_ids: tuple[str, ...],
    presence: dict[str, MonthlyPresenceResult],
    facts: dict[str, RecurrenceCompetitiveFact],
) -> Decimal | None:
    rates: list[Decimal] = []
    for collaborator_id in collaborator_ids:
        rate = facts[collaborator_id].recurrence_rate
        if (
            presence[collaborator_id].worked_days >= MINIMUM_WORKED_DAYS
            and rate is not None
        ):
            rates.append(rate)
    return (
        None
        if not rates
        else sum(rates, start=Decimal("0")) / Decimal(len(rates))
    )


def _presence_by_collaborator(
    facts: tuple[DailyWorkStatusFact, ...], collaborator_ids: tuple[str, ...]
) -> dict[str, MonthlyPresenceResult]:
    grouped: dict[str, list[PresenceDay]] = {
        collaborator_id: [] for collaborator_id in collaborator_ids
    }
    for fact in facts:
        if fact.collaborator_id in grouped:
            grouped[fact.collaborator_id].append(
                PresenceDay(fact.work_date, fact.raw_code)
            )
    return {
        collaborator_id: summarize_monthly_presence(tuple(days))
        for collaborator_id, days in grouped.items()
    }


def _validate_fact_set(
    facts: tuple[
        CsatCompetitiveFact | RecurrenceCompetitiveFact | MonthlyDelayCountFact,
        ...,
    ],
    collaborator_ids: tuple[str, ...],
    name: str,
) -> None:
    identities = tuple(item.collaborator_id for item in facts)
    _validate_unique_identities(identities, f"{name} facts")
    if set(identities) != set(collaborator_ids):
        raise ValueError(f"{name} facts must cover exactly collaborator_ids")


def _validate_unique_identities(values: tuple[str, ...], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


def _validate_identity_and_month(collaborator_id: str, month: date) -> None:
    if not collaborator_id.strip():
        raise ValueError("collaborator_id must not be blank")
    if month.day != 1:
        raise ValueError("reference month must be the first day of a month")


def _validate_decimal(value: Decimal | None, field_name: str) -> None:
    if value is not None and (
        not isinstance(value, Decimal) or not value.is_finite()
    ):
        raise ValueError(f"{field_name} must be a finite Decimal")


def _validate_rate(value: Decimal | None, field_name: str) -> None:
    _validate_decimal(value, field_name)
    if value is not None and not Decimal("0") <= value <= Decimal("1"):
        raise ValueError(f"{field_name} must be between zero and one")


def _previous_month(value: date) -> date:
    if value.month == 1:
        return date(value.year - 1, 12, 1)
    return date(value.year, value.month - 1, 1)
