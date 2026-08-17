from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

MINIMUM_WORKED_DAYS = 20
CSAT_GOLD_AMOUNT = Decimal("800.00")
CSAT_SILVER_AMOUNT = Decimal("200.00")
CSAT_BRONZE_AMOUNT = Decimal("100.00")
RECURRENCE_GOLD_AMOUNT = Decimal("800.00")
RECURRENCE_SILVER_AMOUNT = Decimal("200.00")
RECURRENCE_BRONZE_AMOUNT = Decimal("100.00")
MAXIMUM_POSITIVE_AMOUNT = Decimal("1600.00")
CHAT_MINIMUM_RESPONSE_RATE = Decimal("0.40")
PHONE_MINIMUM_RESPONSE_RATE = Decimal("0.50")
PHONE_COMPETITIVE_MAXIMUM_SCORE = Decimal("10.00")
RECURRENCE_MAXIMUM_POPULATION_AVERAGE = Decimal("0.20")


class CsatCompetitiveChannel(StrEnum):
    CHAT = "chat"
    PHONE = "phone"


class VariableCompensationTier(StrEnum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"


class VariableCompensationComponentStatus(StrEnum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    NOT_EVALUABLE = "not_evaluable"


class MonthlyVariableCompensationStatus(StrEnum):
    CALCULATED = "calculated"
    NOT_EVALUABLE = "not_evaluable"


class VariableCompensationFlag(StrEnum):
    GREEN = "green"
    WHITE = "white"
    RED = "red"


@dataclass(frozen=True, slots=True)
class VariableCompensationCompetence:
    competence_month: date
    csat_reference_month: date
    recurrence_cohort_month: date
    attendance_reference_month: date

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.competence_month, "competence_month"),
            (self.csat_reference_month, "csat_reference_month"),
            (self.recurrence_cohort_month, "recurrence_cohort_month"),
            (self.attendance_reference_month, "attendance_reference_month"),
        ):
            if value.day != 1:
                raise ValueError(f"{field_name} must be the first day of a month")
        if self.csat_reference_month != self.competence_month:
            raise ValueError("CSAT reference month must match competence month")
        if self.attendance_reference_month != self.competence_month:
            raise ValueError("attendance reference month must match competence month")
        if self.recurrence_cohort_month != _previous_month(self.competence_month):
            raise ValueError("recurrence cohort must be the previous month")


@dataclass(frozen=True, slots=True)
class CsatVariableCompensationFacts:
    worked_days: int
    channel: CsatCompetitiveChannel | None = None
    response_rate: Decimal | None = None
    operator_score: Decimal | None = None
    channel_average: Decimal | None = None
    channel_maximum_score: Decimal | None = None

    def __post_init__(self) -> None:
        if self.worked_days < 0:
            raise ValueError("worked_days must not be negative")
        _validate_optional_rate(self.response_rate, "response_rate")
        _validate_optional_decimal(self.operator_score, "operator_score")
        _validate_optional_decimal(self.channel_average, "channel_average")
        _validate_optional_decimal(
            self.channel_maximum_score, "channel_maximum_score"
        )


@dataclass(frozen=True, slots=True)
class RecurrenceVariableCompensationFacts:
    is_eligible: bool
    operator_rate: Decimal | None = None
    population_average_rate: Decimal | None = None

    def __post_init__(self) -> None:
        _validate_optional_rate(self.operator_rate, "operator_rate")
        _validate_optional_rate(
            self.population_average_rate, "population_average_rate"
        )


@dataclass(frozen=True, slots=True)
class MonthlyVariableCompensationInput:
    collaborator_id: str
    competence: VariableCompensationCompetence
    csat: CsatVariableCompensationFacts
    recurrence: RecurrenceVariableCompensationFacts
    delay_count: int
    absence_days: int

    def __post_init__(self) -> None:
        if not self.collaborator_id.strip():
            raise ValueError("collaborator_id must not be blank")
        if self.delay_count < 0:
            raise ValueError("delay_count must not be negative")
        if self.absence_days < 0:
            raise ValueError("absence_days must not be negative")


@dataclass(frozen=True, slots=True)
class VariableCompensationComponentResult:
    reference_month: date
    status: VariableCompensationComponentStatus
    tier: VariableCompensationTier | None
    amount: Decimal | None


@dataclass(frozen=True, slots=True)
class MonthlyVariableCompensationResult:
    collaborator_id: str
    competence: VariableCompensationCompetence
    status: MonthlyVariableCompensationStatus
    csat: VariableCompensationComponentResult
    recurrence: VariableCompensationComponentResult
    delay_discount: Decimal
    absence_discount: Decimal
    total_amount: Decimal | None
    flag: VariableCompensationFlag | None


class MonthlyVariableCompensationEvaluator:
    """Calcula a RV mensal sem acessar fontes, persistência ou Ledger."""

    def evaluate(
        self, facts: MonthlyVariableCompensationInput
    ) -> MonthlyVariableCompensationResult:
        csat = _evaluate_csat(facts.csat, facts.competence.csat_reference_month)
        recurrence = _evaluate_recurrence(
            facts.recurrence, facts.competence.recurrence_cohort_month
        )
        delay_discount = _delay_discount(facts.delay_count)
        absence_discount = _absence_discount(facts.absence_days)
        if any(
            component.status is VariableCompensationComponentStatus.NOT_EVALUABLE
            for component in (csat, recurrence)
        ):
            return MonthlyVariableCompensationResult(
                collaborator_id=facts.collaborator_id,
                competence=facts.competence,
                status=MonthlyVariableCompensationStatus.NOT_EVALUABLE,
                csat=csat,
                recurrence=recurrence,
                delay_discount=delay_discount,
                absence_discount=absence_discount,
                total_amount=None,
                flag=None,
            )
        total = (
            _component_amount(csat)
            + _component_amount(recurrence)
            + delay_discount
            + absence_discount
        )
        return MonthlyVariableCompensationResult(
            collaborator_id=facts.collaborator_id,
            competence=facts.competence,
            status=MonthlyVariableCompensationStatus.CALCULATED,
            csat=csat,
            recurrence=recurrence,
            delay_discount=delay_discount,
            absence_discount=absence_discount,
            total_amount=total,
            flag=_flag(total),
        )


def _evaluate_csat(
    facts: CsatVariableCompensationFacts, reference_month: date
) -> VariableCompensationComponentResult:
    if facts.worked_days < MINIMUM_WORKED_DAYS:
        return _component_result(
            reference_month, VariableCompensationComponentStatus.NOT_ELIGIBLE
        )
    if facts.channel is None or facts.response_rate is None:
        return _component_result(
            reference_month, VariableCompensationComponentStatus.NOT_EVALUABLE
        )
    minimum_response_rate = (
        CHAT_MINIMUM_RESPONSE_RATE
        if facts.channel is CsatCompetitiveChannel.CHAT
        else PHONE_MINIMUM_RESPONSE_RATE
    )
    if facts.response_rate < minimum_response_rate:
        return _component_result(
            reference_month, VariableCompensationComponentStatus.NOT_ELIGIBLE
        )
    if facts.operator_score is None or facts.channel_average is None:
        return _component_result(
            reference_month, VariableCompensationComponentStatus.NOT_EVALUABLE
        )
    if facts.channel is CsatCompetitiveChannel.CHAT:
        if facts.operator_score >= Decimal("9.50"):
            return _awarded(reference_month, VariableCompensationTier.GOLD)
    else:
        maximum = facts.channel_maximum_score
        if maximum is None or facts.operator_score > maximum:
            return _component_result(
                reference_month, VariableCompensationComponentStatus.NOT_EVALUABLE
            )
        if facts.operator_score == maximum:
            return _awarded(reference_month, VariableCompensationTier.GOLD)
    difference = facts.operator_score - facts.channel_average
    if difference >= Decimal("0.10"):
        return _awarded(reference_month, VariableCompensationTier.SILVER)
    if difference >= Decimal("0.05"):
        return _awarded(reference_month, VariableCompensationTier.BRONZE)
    return _component_result(
        reference_month,
        VariableCompensationComponentStatus.ELIGIBLE,
        amount=Decimal("0.00"),
    )


def _evaluate_recurrence(
    facts: RecurrenceVariableCompensationFacts, reference_month: date
) -> VariableCompensationComponentResult:
    if not facts.is_eligible:
        return _component_result(
            reference_month, VariableCompensationComponentStatus.NOT_ELIGIBLE
        )
    if facts.operator_rate is None or facts.population_average_rate is None:
        return _component_result(
            reference_month, VariableCompensationComponentStatus.NOT_EVALUABLE
        )
    if (
        facts.population_average_rate
        > RECURRENCE_MAXIMUM_POPULATION_AVERAGE
    ):
        return _component_result(
            reference_month,
            VariableCompensationComponentStatus.ELIGIBLE,
            amount=Decimal("0.00"),
        )
    difference = facts.population_average_rate - facts.operator_rate
    if difference >= Decimal("0.12"):
        return _awarded(
            reference_month,
            VariableCompensationTier.GOLD,
            recurrence=True,
        )
    if difference >= Decimal("0.05"):
        return _awarded(
            reference_month,
            VariableCompensationTier.SILVER,
            recurrence=True,
        )
    if difference >= Decimal("0.03"):
        return _awarded(
            reference_month,
            VariableCompensationTier.BRONZE,
            recurrence=True,
        )
    return _component_result(
        reference_month,
        VariableCompensationComponentStatus.ELIGIBLE,
        amount=Decimal("0.00"),
    )


def _awarded(
    reference_month: date,
    tier: VariableCompensationTier,
    *,
    recurrence: bool = False,
) -> VariableCompensationComponentResult:
    amounts = (
        {
            VariableCompensationTier.GOLD: RECURRENCE_GOLD_AMOUNT,
            VariableCompensationTier.SILVER: RECURRENCE_SILVER_AMOUNT,
            VariableCompensationTier.BRONZE: RECURRENCE_BRONZE_AMOUNT,
        }
        if recurrence
        else {
            VariableCompensationTier.GOLD: CSAT_GOLD_AMOUNT,
            VariableCompensationTier.SILVER: CSAT_SILVER_AMOUNT,
            VariableCompensationTier.BRONZE: CSAT_BRONZE_AMOUNT,
        }
    )
    return _component_result(
        reference_month,
        VariableCompensationComponentStatus.ELIGIBLE,
        tier=tier,
        amount=amounts[tier],
    )


def _component_result(
    reference_month: date,
    status: VariableCompensationComponentStatus,
    *,
    tier: VariableCompensationTier | None = None,
    amount: Decimal | None = None,
) -> VariableCompensationComponentResult:
    if status is VariableCompensationComponentStatus.NOT_ELIGIBLE:
        amount = Decimal("0.00")
    return VariableCompensationComponentResult(
        reference_month=reference_month,
        status=status,
        tier=tier,
        amount=amount,
    )


def _delay_discount(delay_count: int) -> Decimal:
    if delay_count == 0:
        return Decimal("0.00")
    if delay_count <= 2:
        return Decimal("-25.00")
    if delay_count <= 9:
        return Decimal("-50.00")
    return Decimal("-250.00")


def _absence_discount(absence_days: int) -> Decimal:
    if absence_days == 0:
        return Decimal("0.00")
    if absence_days == 1:
        return Decimal("-50.00")
    if absence_days == 2:
        return Decimal("-75.00")
    return Decimal("-250.00")


def _flag(amount: Decimal) -> VariableCompensationFlag:
    if amount > 0:
        return VariableCompensationFlag.GREEN
    if amount < 0:
        return VariableCompensationFlag.RED
    return VariableCompensationFlag.WHITE


def _component_amount(result: VariableCompensationComponentResult) -> Decimal:
    if result.amount is None:
        raise ValueError("evaluable component must have an amount")
    return result.amount


def _validate_optional_decimal(value: Decimal | None, field_name: str) -> None:
    if value is not None and (not isinstance(value, Decimal) or not value.is_finite()):
        raise ValueError(f"{field_name} must be a finite Decimal")


def _validate_optional_rate(value: Decimal | None, field_name: str) -> None:
    _validate_optional_decimal(value, field_name)
    if value is not None and not Decimal("0") <= value <= Decimal("1"):
        raise ValueError(f"{field_name} must be between zero and one")


def _previous_month(value: date) -> date:
    if value.month == 1:
        return date(value.year - 1, 12, 1)
    return date(value.year, value.month - 1, 1)
