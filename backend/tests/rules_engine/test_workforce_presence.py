from datetime import date, timedelta

import pytest

from supervisor_ai.rules_engine import (
    PresenceDay,
    PresenceDayCategory,
    classify_presence_code,
    summarize_monthly_presence,
)


@pytest.mark.parametrize("code", ("P", "PS", "PD", "PF", "FT", "EX", "PL"))
def test_confirmed_work_codes_count_as_worked_day(code: str) -> None:
    assert classify_presence_code(code) is PresenceDayCategory.WORKED_DAY


@pytest.mark.parametrize("code", ("A", "F", "OF"))
def test_confirmed_penalizable_absences_do_not_count_as_work(code: str) -> None:
    result = summarize_monthly_presence((PresenceDay(date(2026, 8, 1), code),))

    assert result.worked_days == 0
    assert result.penalizable_absence_days == 1


def test_time_bank_is_non_penalizable_and_does_not_count_as_work() -> None:
    result = summarize_monthly_presence((PresenceDay(date(2026, 8, 1), "B.H"),))

    assert result.worked_days == 0
    assert result.penalizable_absence_days == 0
    assert result.non_penalizable_absence_days == 1


@pytest.mark.parametrize("worked_days", (19, 20, 21))
def test_twenty_worked_day_threshold(worked_days: int) -> None:
    start = date(2026, 8, 1)
    result = summarize_monthly_presence(
        tuple(
            PresenceDay(start + timedelta(days=index), "P")
            for index in range(worked_days)
        )
    )

    assert result.meets_minimum_worked_days is (worked_days >= 20)


@pytest.mark.parametrize("code", ("FE", "D", "D.O", "DF"))
def test_non_working_codes_do_not_gain_monetary_meaning(code: str) -> None:
    assert classify_presence_code(code) is PresenceDayCategory.NON_WORKING_DAY


def test_unknown_code_is_preserved_without_invented_classification() -> None:
    day = PresenceDay(date(2026, 8, 1), "L")

    assert day.raw_code == "L"
    assert day.category is PresenceDayCategory.UNCLASSIFIED
