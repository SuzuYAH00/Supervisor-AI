from dataclasses import dataclass
from datetime import date
from enum import StrEnum

MINIMUM_MONTHLY_WORKED_DAYS = 20

_WORKED_CODES = frozenset({"P", "PS", "PD", "PF", "FT", "EX", "PL"})
_PENALIZABLE_ABSENCE_CODES = frozenset({"A", "F", "OF"})
_NON_PENALIZABLE_ABSENCE_CODES = frozenset({"B.H"})
_NON_WORKING_CODES = frozenset({"FE", "D", "D.O", "DF"})


class PresenceDayCategory(StrEnum):
    WORKED_DAY = "worked_day"
    PENALIZABLE_ABSENCE = "penalizable_absence"
    NON_PENALIZABLE_ABSENCE = "non_penalizable_absence"
    NON_WORKING_DAY = "non_working_day"
    UNCLASSIFIED = "unclassified"


@dataclass(frozen=True, slots=True)
class PresenceDay:
    work_date: date
    raw_code: str

    def __post_init__(self) -> None:
        if not self.raw_code or self.raw_code != self.raw_code.strip():
            raise ValueError("raw_code must be non-blank and trimmed")

    @property
    def category(self) -> PresenceDayCategory:
        return classify_presence_code(self.raw_code)


@dataclass(frozen=True, slots=True)
class MonthlyPresenceResult:
    worked_days: int
    penalizable_absence_days: int
    non_penalizable_absence_days: int
    meets_minimum_worked_days: bool


def classify_presence_code(raw_code: str) -> PresenceDayCategory:
    if raw_code in _WORKED_CODES:
        return PresenceDayCategory.WORKED_DAY
    if raw_code in _PENALIZABLE_ABSENCE_CODES:
        return PresenceDayCategory.PENALIZABLE_ABSENCE
    if raw_code in _NON_PENALIZABLE_ABSENCE_CODES:
        return PresenceDayCategory.NON_PENALIZABLE_ABSENCE
    if raw_code in _NON_WORKING_CODES:
        return PresenceDayCategory.NON_WORKING_DAY
    return PresenceDayCategory.UNCLASSIFIED


def summarize_monthly_presence(
    days: tuple[PresenceDay, ...],
) -> MonthlyPresenceResult:
    if len({day.work_date for day in days}) != len(days):
        raise ValueError("presence days must have unique dates")
    worked_days = sum(
        day.category is PresenceDayCategory.WORKED_DAY for day in days
    )
    penalizable_absence_days = sum(
        day.category is PresenceDayCategory.PENALIZABLE_ABSENCE for day in days
    )
    non_penalizable_absence_days = sum(
        day.category is PresenceDayCategory.NON_PENALIZABLE_ABSENCE
        for day in days
    )
    return MonthlyPresenceResult(
        worked_days=worked_days,
        penalizable_absence_days=penalizable_absence_days,
        non_penalizable_absence_days=non_penalizable_absence_days,
        meets_minimum_worked_days=worked_days >= MINIMUM_MONTHLY_WORKED_DAYS,
    )
