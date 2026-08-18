from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum


class DelayOccurrenceType(StrEnum):
    ENTRY = "entry"
    PAUSE_DURATION = "pause_duration"


class DelayDecision(StrEnum):
    VALID = "valid"
    CORRECTED = "corrected"


@dataclass(frozen=True, slots=True)
class PauseDelayEvaluation:
    is_delay: bool
    applied_limit_seconds: int | None


def evaluate_pause_delay(
    *, pause_type: str, duration_seconds: int
) -> PauseDelayEvaluation:
    if duration_seconds < 0:
        raise ValueError("duration_seconds must not be negative")
    limits = {
        "Intervalo 20min": 20 * 60 + 59,
        "Banheiro": 5 * 60,
    }
    limit = limits.get(pause_type)
    return PauseDelayEvaluation(
        is_delay=limit is not None and duration_seconds > limit,
        applied_limit_seconds=limit,
    )


def evaluate_entry_delay(*, planned_start: time, observed_start: time) -> bool:
    """O minuto planejado inteiro é pontual; o minuto seguinte é atraso."""
    planned = planned_start.hour * 3600 + planned_start.minute * 60
    observed = (
        observed_start.hour * 3600 + observed_start.minute * 60 + observed_start.second
    )
    return observed > planned + 59


def month_bounds(competence_month: date) -> tuple[date, date]:
    if competence_month.day != 1:
        raise ValueError("competence_month must be the first day of a month")
    if competence_month.month == 12:
        following = date(competence_month.year + 1, 1, 1)
    else:
        following = date(competence_month.year, competence_month.month + 1, 1)
    return competence_month, date.fromordinal(following.toordinal() - 1)
