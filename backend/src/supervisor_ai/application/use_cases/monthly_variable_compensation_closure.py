from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from supervisor_ai.application.errors import (
    IngestionCoverageUnknown,
    WorkScheduleIncomplete,
)
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.application.use_cases.calculate_monthly_variable_compensation import (  # noqa: E501
    CalculateMonthlyVariableCompensationCommand,
    CalculateMonthlyVariableCompensationUseCase,
    CsatCompetitiveFact,
    MonthlyDelayCountFact,
    RecurrenceCompetitiveFact,
)
from supervisor_ai.application.use_cases.get_monthly_csat_facts import (
    GetMonthlyCsatFactsQuery,
    GetMonthlyCsatFactsUseCase,
)
from supervisor_ai.application.use_cases.get_monthly_recurrence_facts import (
    GetMonthlyRecurrenceFactsQuery,
    GetMonthlyRecurrenceFactsUseCase,
    MonthlyRecurrenceFact,
)
from supervisor_ai.application.use_cases.npx_delays import (
    GetMonthlyDelayFactsFromCoverageUseCase,
    GetMonthlyDelayFactsQuery,
)
from supervisor_ai.rules_engine import (
    CHAT_MINIMUM_RESPONSE_RATE,
    PHONE_MINIMUM_RESPONSE_RATE,
    RECURRENCE_MAXIMUM_POPULATION_AVERAGE,
    CsatCompetitiveChannel,
    MonthlyVariableCompensationStatus,
    VariableCompensationComponentResult,
)


class ClosureStatus(StrEnum):
    CALCULATED = "calculated"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class GetMonthlyVariableCompensationClosureQuery:
    competence_month: date
    collaborator_id: str | None = None
    status: ClosureStatus | None = None

    def __post_init__(self) -> None:
        if self.competence_month.day != 1:
            raise ValueError("competence_month must be the first day of a month")
        if self.collaborator_id is not None and not self.collaborator_id.strip():
            raise ValueError("collaborator_id must not be blank")


@dataclass(frozen=True, slots=True)
class ClosureComponent:
    status: str
    reference_month: date
    eligible: bool
    tier: str | None
    amount: Decimal | None
    individual_value: Decimal | None
    team_average: Decimal | None


@dataclass(frozen=True, slots=True)
class CsatClosureComponent:
    result: ClosureComponent
    modality: str
    eligible_contact_count: int
    valid_response_count: int
    raw_average: Decimal | None
    response_rate: Decimal | None
    minimum_response_rate: Decimal


@dataclass(frozen=True, slots=True)
class RecurrenceClosureComponent:
    result: ClosureComponent
    eligible_attendance_count: int
    recurrence_count: int
    team_average_cap_passed: bool | None


@dataclass(frozen=True, slots=True)
class DeductionClosureComponent:
    count: int | None
    amount: Decimal | None


@dataclass(frozen=True, slots=True)
class MonthlyVariableCompensationClosureItem:
    collaborator_id: str
    display_name: str
    competence_month: date
    status: ClosureStatus
    pending_reasons: tuple[str, ...]
    current_worked_days: int
    previous_worked_days: int
    csat: CsatClosureComponent
    recurrence: RecurrenceClosureComponent
    delays: DeductionClosureComponent
    absences: DeductionClosureComponent
    positive_amount: Decimal | None
    deductions_amount: Decimal | None
    total_amount: Decimal | None
    flag: str | None


@dataclass(frozen=True, slots=True)
class GetMonthlyVariableCompensationClosureResult:
    competence_month: date
    collaborator_count: int
    calculated_count: int
    incomplete_count: int
    projected_total: Decimal | None
    items: tuple[MonthlyVariableCompensationClosureItem, ...]


class GetMonthlyVariableCompensationClosureUseCase:
    """Explica a composição existente sem reproduzir suas regras monetárias."""

    def __init__(
        self,
        factory: UnitOfWorkFactory,
        calculator: CalculateMonthlyVariableCompensationUseCase,
        csat: GetMonthlyCsatFactsUseCase,
        recurrence: GetMonthlyRecurrenceFactsUseCase,
        delays: GetMonthlyDelayFactsFromCoverageUseCase,
    ) -> None:
        self._factory = factory
        self._calculator = calculator
        self._csat = csat
        self._recurrence = recurrence
        self._delays = delays

    def execute(
        self, query: GetMonthlyVariableCompensationClosureQuery
    ) -> GetMonthlyVariableCompensationClosureResult:
        with self._factory() as uow:
            profiles = uow.operational_collaborators.list_all()
        collaborator_ids = tuple(
            item.collaborator_id
            for item in profiles
            if query.collaborator_id is None
            or item.collaborator_id == query.collaborator_id
        )
        if not collaborator_ids:
            return GetMonthlyVariableCompensationClosureResult(
                query.competence_month, 0, 0, 0, Decimal("0.00"), ()
            )
        previous_month = _previous_month(query.competence_month)
        csat_result = self._csat.execute(
            GetMonthlyCsatFactsQuery(query.competence_month, collaborator_ids)
        )
        pending: list[str] = []
        recurrence_items: tuple[MonthlyRecurrenceFact, ...]
        try:
            recurrence_items = self._recurrence.execute(
                GetMonthlyRecurrenceFactsQuery(previous_month, collaborator_ids)
            ).items
        except (IngestionCoverageUnknown, ValueError) as error:
            pending.append(f"recurrence_incomplete:{error}")
            recurrence_items = tuple(
                MonthlyRecurrenceFact(item, previous_month, 0, 0, None)
                for item in collaborator_ids
            )
        delay_counts: dict[str, int] = {}
        try:
            delay_counts = {
                item.collaborator_id: item.delay_count
                for item in self._delays.execute(
                    GetMonthlyDelayFactsQuery(query.competence_month, collaborator_ids)
                ).items
            }
        except WorkScheduleIncomplete as error:
            pending.append(f"delays_incomplete:{error}")
        calculation = self._calculator.execute(
            CalculateMonthlyVariableCompensationCommand(
                query.competence_month,
                collaborator_ids,
                delay_facts=tuple(
                    MonthlyDelayCountFact(
                        item, query.competence_month, delay_counts.get(item, 0)
                    )
                    for item in collaborator_ids
                ),
                csat_facts=tuple(
                    CsatCompetitiveFact(
                        item.collaborator_id,
                        item.reference_month,
                        item.competitive_score,
                        item.response_rate,
                    )
                    for item in csat_result.items
                ),
                recurrence_facts=tuple(
                    RecurrenceCompetitiveFact(
                        item.collaborator_id,
                        item.cohort_month,
                        item.recurrence_rate,
                    )
                    for item in recurrence_items
                ),
            )
        )
        csat_by_id = {item.collaborator_id: item for item in csat_result.items}
        recurrence_by_id = {item.collaborator_id: item for item in recurrence_items}
        inputs = {item.collaborator_id: item for item in calculation.resolved_inputs}
        results = {item.collaborator_id: item for item in calculation.items}
        previous_presence = dict(calculation.previous_presence)
        current_presence_counts = dict(calculation.current_presence_fact_counts)
        previous_presence_counts = dict(calculation.previous_presence_fact_counts)
        items = tuple(
            self._item(
                collaborator_id,
                csat_by_id[collaborator_id],
                recurrence_by_id[collaborator_id],
                inputs[collaborator_id],
                results[collaborator_id],
                delay_counts.get(collaborator_id),
                tuple(pending),
                previous_presence[collaborator_id].worked_days,
                current_presence_counts[collaborator_id],
                previous_presence_counts[collaborator_id],
            )
            for collaborator_id in collaborator_ids
        )
        filtered = tuple(
            item
            for item in items
            if query.status is None or item.status is query.status
        )
        calculated_count = sum(
            item.status is ClosureStatus.CALCULATED for item in items
        )
        total = (
            sum((item.total_amount for item in items), start=Decimal("0"))
            if calculated_count == len(items)
            else None
        )
        return GetMonthlyVariableCompensationClosureResult(
            query.competence_month,
            len(items),
            calculated_count,
            len(items) - calculated_count,
            total,
            filtered,
        )

    def _item(
        self,
        collaborator_id,
        csat,
        recurrence,
        facts,
        result,
        delay_count,
        pending,
        previous_worked_days,
        current_presence_fact_count,
        previous_presence_fact_count,
    ):
        reasons = list(pending)
        if current_presence_fact_count == 0:
            reasons.append("presence_current_month_missing")
        if previous_presence_fact_count == 0:
            reasons.append("presence_previous_month_missing")
        if result.csat.status.value == "not_evaluable":
            reasons.append(
                "csat_no_eligible_contacts"
                if csat.eligible_contact_count == 0
                else "csat_not_evaluable"
            )
        if result.recurrence.status.value == "not_evaluable" and not any(
            reason.startswith("recurrence_incomplete") for reason in reasons
        ):
            reasons.append("recurrence_not_evaluable")
        status = (
            ClosureStatus.CALCULATED
            if result.status is MonthlyVariableCompensationStatus.CALCULATED
            and not reasons
            and delay_count is not None
            else ClosureStatus.INCOMPLETE
        )
        csat_result = _component(
            result.csat, facts.csat.operator_score, facts.csat.channel_average
        )
        recurrence_result = _component(
            result.recurrence,
            facts.recurrence.operator_rate,
            facts.recurrence.population_average_rate,
        )
        positive = None
        deductions = None
        if status is ClosureStatus.CALCULATED:
            positive = (result.csat.amount or Decimal("0")) + (
                result.recurrence.amount or Decimal("0")
            )
            deductions = result.delay_discount + result.absence_discount
        return MonthlyVariableCompensationClosureItem(
            collaborator_id,
            collaborator_id,
            result.competence.competence_month,
            status,
            tuple(reasons),
            facts.csat.worked_days,
            previous_worked_days,
            CsatClosureComponent(
                csat_result,
                facts.csat.channel.value,
                csat.eligible_contact_count,
                csat.valid_response_count,
                csat.raw_average,
                csat.response_rate,
                CHAT_MINIMUM_RESPONSE_RATE
                if facts.csat.channel is CsatCompetitiveChannel.CHAT
                else PHONE_MINIMUM_RESPONSE_RATE,
            ),
            RecurrenceClosureComponent(
                recurrence_result,
                recurrence.eligible_attendance_count,
                recurrence.recurrence_count,
                None
                if facts.recurrence.population_average_rate is None
                else facts.recurrence.population_average_rate
                <= RECURRENCE_MAXIMUM_POPULATION_AVERAGE,
            ),
            DeductionClosureComponent(
                delay_count, result.delay_discount if delay_count is not None else None
            ),
            DeductionClosureComponent(facts.absence_days, result.absence_discount),
            positive,
            deductions,
            result.total_amount if status is ClosureStatus.CALCULATED else None,
            result.flag.value
            if result.flag is not None and status is ClosureStatus.CALCULATED
            else None,
        )


def _component(
    result: VariableCompensationComponentResult,
    individual: Decimal | None,
    average: Decimal | None,
) -> ClosureComponent:
    return ClosureComponent(
        result.status.value,
        result.reference_month,
        result.status.value == "eligible",
        None if result.tier is None else result.tier.value,
        result.amount,
        individual,
        average,
    )


def _previous_month(value: date) -> date:
    return (
        date(value.year - 1, 12, 1)
        if value.month == 1
        else date(value.year, value.month - 1, 1)
    )
