from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from inspect import getsource
from typing import get_type_hints

import pytest

import supervisor_ai.rules_engine.monthly_variable_compensation as module
from supervisor_ai.rules_engine import (
    MAXIMUM_POSITIVE_AMOUNT,
    CsatCompetitiveChannel,
    CsatVariableCompensationFacts,
    MonthlyVariableCompensationEvaluator,
    MonthlyVariableCompensationInput,
    MonthlyVariableCompensationResult,
    MonthlyVariableCompensationStatus,
    RecurrenceVariableCompensationFacts,
    VariableCompensationCompetence,
    VariableCompensationComponentStatus,
    VariableCompensationFlag,
    VariableCompensationTier,
)


def competence() -> VariableCompensationCompetence:
    return VariableCompensationCompetence(
        competence_month=date(2026, 8, 1),
        csat_reference_month=date(2026, 8, 1),
        recurrence_cohort_month=date(2026, 7, 1),
        attendance_reference_month=date(2026, 8, 1),
    )


def csat(
    score: str,
    average: str,
    *,
    channel: CsatCompetitiveChannel = CsatCompetitiveChannel.CHAT,
    maximum: str | None = None,
    worked_days: int = 20,
) -> CsatVariableCompensationFacts:
    return CsatVariableCompensationFacts(
        worked_days=worked_days,
        channel=channel,
        response_rate=Decimal("1.00"),
        operator_score=Decimal(score),
        channel_average=Decimal(average),
        channel_maximum_score=None if maximum is None else Decimal(maximum),
    )


def recurrence(
    operator_rate: str,
    average_rate: str,
    *,
    is_eligible: bool = True,
) -> RecurrenceVariableCompensationFacts:
    return RecurrenceVariableCompensationFacts(
        is_eligible=is_eligible,
        operator_rate=Decimal(operator_rate),
        population_average_rate=Decimal(average_rate),
    )


def evaluate(
    *,
    csat_facts: CsatVariableCompensationFacts | None = None,
    recurrence_facts: RecurrenceVariableCompensationFacts | None = None,
    delays: int = 0,
    absences: int = 0,
) -> MonthlyVariableCompensationResult:
    return MonthlyVariableCompensationEvaluator().evaluate(
        MonthlyVariableCompensationInput(
            collaborator_id="operator-1",
            competence=competence(),
            csat=csat_facts or csat("9.50", "9.00"),
            recurrence=recurrence_facts or recurrence("0.08", "0.20"),
            delay_count=delays,
            absence_days=absences,
        )
    )


@pytest.mark.parametrize(
    ("score", "average", "expected_tier", "expected_amount"),
    [
        ("9.50", "9.60", VariableCompensationTier.GOLD, Decimal("800.00")),
        ("9.40", "9.30", VariableCompensationTier.SILVER, Decimal("200.00")),
        ("9.35", "9.30", VariableCompensationTier.BRONZE, Decimal("100.00")),
        ("9.34", "9.30", None, Decimal("0.00")),
    ],
)
def test_chat_tiers_and_exact_boundaries(
    score: str,
    average: str,
    expected_tier: VariableCompensationTier | None,
    expected_amount: Decimal,
) -> None:
    result = evaluate(csat_facts=csat(score, average)).csat

    assert result.status is VariableCompensationComponentStatus.ELIGIBLE
    assert result.tier is expected_tier
    assert result.amount == expected_amount


def test_chat_gold_has_priority_over_relative_tiers() -> None:
    result = evaluate(csat_facts=csat("9.50", "9.45")).csat

    assert result.tier is VariableCompensationTier.GOLD
    assert result.amount == Decimal("800.00")


@pytest.mark.parametrize(
    ("score", "average", "maximum", "expected_tier", "expected_amount"),
    [
        ("10.00", "9.95", "10.00", VariableCompensationTier.GOLD, "800.00"),
        ("9.90", "9.80", "10.00", VariableCompensationTier.SILVER, "200.00"),
        ("9.85", "9.80", "10.00", VariableCompensationTier.BRONZE, "100.00"),
        ("9.84", "9.80", "10.00", None, "0.00"),
    ],
)
def test_phone_tiers_use_the_factual_channel_maximum(
    score: str,
    average: str,
    maximum: str,
    expected_tier: VariableCompensationTier | None,
    expected_amount: str,
) -> None:
    result = evaluate(
        csat_facts=csat(
            score,
            average,
            channel=CsatCompetitiveChannel.PHONE,
            maximum=maximum,
        )
    ).csat

    assert result.tier is expected_tier
    assert result.amount == Decimal(expected_amount)


def test_phone_without_factual_maximum_is_not_evaluable() -> None:
    result = evaluate(
        csat_facts=csat(
            "9.90",
            "9.80",
            channel=CsatCompetitiveChannel.PHONE,
        )
    )

    assert result.csat.status is VariableCompensationComponentStatus.NOT_EVALUABLE
    assert result.csat.amount is None
    assert result.status is MonthlyVariableCompensationStatus.NOT_EVALUABLE
    assert result.total_amount is None
    assert result.flag is None


@pytest.mark.parametrize(
    ("channel", "response_rate", "expected_status"),
    (
        (CsatCompetitiveChannel.CHAT, "0.39", "not_eligible"),
        (CsatCompetitiveChannel.CHAT, "0.40", "eligible"),
        (CsatCompetitiveChannel.PHONE, "0.49", "not_eligible"),
        (CsatCompetitiveChannel.PHONE, "0.50", "eligible"),
    ),
)
def test_csat_preserves_minimum_response_rate_by_competitive_channel(
    channel: CsatCompetitiveChannel,
    response_rate: str,
    expected_status: str,
) -> None:
    facts = csat(
        "9.00",
        "9.00",
        channel=channel,
        maximum="10.00" if channel is CsatCompetitiveChannel.PHONE else None,
    )
    facts = CsatVariableCompensationFacts(
        worked_days=facts.worked_days,
        channel=facts.channel,
        response_rate=Decimal(response_rate),
        operator_score=facts.operator_score,
        channel_average=facts.channel_average,
        channel_maximum_score=facts.channel_maximum_score,
    )

    assert evaluate(csat_facts=facts).csat.status.value == expected_status


def test_csat_has_exactly_one_competitive_channel() -> None:
    facts = csat("9.50", "9.00", channel=CsatCompetitiveChannel.CHAT)

    assert facts.channel is CsatCompetitiveChannel.CHAT
    assert not hasattr(facts, "phone_score")
    assert not hasattr(facts, "chat_score")


@pytest.mark.parametrize(
    ("operator_rate", "expected_tier", "expected_amount"),
    [
        ("0.17", VariableCompensationTier.BRONZE, "100.00"),
        ("0.15", VariableCompensationTier.SILVER, "200.00"),
        ("0.08", VariableCompensationTier.GOLD, "800.00"),
        ("0.07", VariableCompensationTier.GOLD, "800.00"),
        ("0.171", None, "0.00"),
    ],
)
def test_recurrence_tiers_use_percentage_point_difference(
    operator_rate: str,
    expected_tier: VariableCompensationTier | None,
    expected_amount: str,
) -> None:
    result = evaluate(
        recurrence_facts=recurrence(operator_rate, "0.20")
    ).recurrence

    assert result.tier is expected_tier
    assert result.amount == Decimal(expected_amount)


def test_recurrence_does_not_use_relative_reduction() -> None:
    result = evaluate(
        recurrence_facts=recurrence("0.188", "0.20")
    ).recurrence

    assert result.tier is None
    assert result.amount == Decimal("0.00")


def test_recurrence_population_average_above_twenty_percent_blocks_awards() -> None:
    result = evaluate(
        recurrence_facts=recurrence("0.01", "0.201")
    ).recurrence

    assert result.status is VariableCompensationComponentStatus.ELIGIBLE
    assert result.tier is None
    assert result.amount == Decimal("0.00")


@pytest.mark.parametrize(
    ("delay_count", "expected"),
    [
        (0, "0.00"),
        (1, "-25.00"),
        (2, "-25.00"),
        (3, "-50.00"),
        (9, "-50.00"),
        (10, "-250.00"),
    ],
)
def test_delay_discount_is_non_cumulative(
    delay_count: int, expected: str
) -> None:
    result = evaluate(delays=delay_count)

    assert result.delay_discount == Decimal(expected)


@pytest.mark.parametrize(
    ("absence_days", "expected"),
    [(0, "0.00"), (1, "-50.00"), (2, "-75.00"), (3, "-250.00")],
)
def test_absence_discount_is_non_cumulative(
    absence_days: int, expected: str
) -> None:
    result = evaluate(absences=absence_days)

    assert result.absence_discount == Decimal(expected)


def test_discount_categories_compose_independently() -> None:
    result = evaluate(delays=1, absences=1)

    assert result.delay_discount == Decimal("-25.00")
    assert result.absence_discount == Decimal("-50.00")
    assert result.total_amount == Decimal("1525.00")


def test_maximum_positive_result_is_exactly_sixteen_hundred() -> None:
    result = evaluate()

    assert result.total_amount == MAXIMUM_POSITIVE_AMOUNT == Decimal("1600.00")
    assert result.flag is VariableCompensationFlag.GREEN


def test_intermediate_result_matches_normative_example() -> None:
    result = evaluate(
        recurrence_facts=recurrence("0.15", "0.20"),
        delays=1,
        absences=1,
    )

    assert result.total_amount == Decimal("925.00")


@pytest.mark.parametrize(
    ("delays", "expected_total", "expected_flag"),
    [
        (0, Decimal("0.00"), VariableCompensationFlag.WHITE),
        (1, Decimal("-25.00"), VariableCompensationFlag.RED),
    ],
)
def test_zero_and_negative_results_are_preserved_without_floor(
    delays: int,
    expected_total: Decimal,
    expected_flag: VariableCompensationFlag,
) -> None:
    result = evaluate(
        csat_facts=csat("9.00", "9.00"),
        recurrence_facts=recurrence("0.20", "0.20"),
        delays=delays,
    )

    assert result.total_amount == expected_total
    assert result.flag is expected_flag


def test_twenty_or_more_days_receive_full_csat_without_proportionality() -> None:
    twenty_days = evaluate(csat_facts=csat("9.50", "9.00", worked_days=20))
    twenty_five_days = evaluate(csat_facts=csat("9.50", "9.00", worked_days=25))

    assert twenty_days.csat.amount == twenty_five_days.csat.amount == Decimal("800.00")


def test_non_eligible_component_differs_from_eligible_zero() -> None:
    non_eligible = evaluate(
        csat_facts=csat("9.50", "9.00", worked_days=19),
        recurrence_facts=recurrence("0.20", "0.20"),
    )
    eligible_zero = evaluate(
        csat_facts=csat("9.00", "9.00", worked_days=20),
        recurrence_facts=recurrence("0.20", "0.20"),
    )

    assert non_eligible.csat.status is (
        VariableCompensationComponentStatus.NOT_ELIGIBLE
    )
    assert eligible_zero.csat.status is VariableCompensationComponentStatus.ELIGIBLE
    assert non_eligible.csat.amount == eligible_zero.csat.amount == Decimal("0.00")


def test_vacation_month_can_exclude_csat_but_keep_prior_cohort_recurrence() -> None:
    result = evaluate(
        csat_facts=CsatVariableCompensationFacts(worked_days=0),
        recurrence_facts=recurrence("0.15", "0.20"),
    )

    assert result.csat.status is VariableCompensationComponentStatus.NOT_ELIGIBLE
    assert result.csat.reference_month == date(2026, 8, 1)
    assert result.recurrence.status is VariableCompensationComponentStatus.ELIGIBLE
    assert result.recurrence.reference_month == date(2026, 7, 1)
    assert result.recurrence.amount == result.total_amount == Decimal("200.00")


def test_recurrence_can_be_explicitly_not_eligible_without_blocking_total() -> None:
    result = evaluate(
        recurrence_facts=RecurrenceVariableCompensationFacts(is_eligible=False)
    )

    assert result.recurrence.status is (
        VariableCompensationComponentStatus.NOT_ELIGIBLE
    )
    assert result.recurrence.amount == Decimal("0.00")
    assert result.total_amount == Decimal("800.00")


def test_competence_preserves_distinct_factual_months() -> None:
    result = evaluate()

    assert result.competence.competence_month == date(2026, 8, 1)
    assert result.csat.reference_month == date(2026, 8, 1)
    assert result.recurrence.reference_month == date(2026, 7, 1)
    assert result.competence.attendance_reference_month == date(2026, 8, 1)


def test_missing_eligible_component_facts_prevent_financial_materialization() -> None:
    result = evaluate(
        recurrence_facts=RecurrenceVariableCompensationFacts(is_eligible=True)
    )

    assert result.recurrence.status is (
        VariableCompensationComponentStatus.NOT_EVALUABLE
    )
    assert result.total_amount is None
    assert result.flag is None


def test_contracts_are_immutable_and_require_decimal_facts() -> None:
    facts = csat("9.50", "9.00")
    hints = get_type_hints(CsatVariableCompensationFacts)

    with pytest.raises(FrozenInstanceError):
        facts.worked_days = 10
    assert "float" not in str(hints["operator_score"])
    assert "float" not in str(hints["channel_average"])
    assert "float" not in str(hints["channel_maximum_score"])


def test_competence_rejects_wrong_reference_months() -> None:
    with pytest.raises(ValueError, match="previous month"):
        VariableCompensationCompetence(
            competence_month=date(2026, 8, 1),
            csat_reference_month=date(2026, 8, 1),
            recurrence_cohort_month=date(2026, 8, 1),
            attendance_reference_month=date(2026, 8, 1),
        )


def test_rule_has_no_http_persistence_ledger_or_quality_dependency() -> None:
    source = getsource(module).lower()

    assert "fastapi" not in source
    assert "sqlalchemy" not in source
    assert "supervisor_ai.application" not in source
    assert "supervisor_ai.infrastructure" not in source
    assert "remuneration_ledger" not in source
    assert "quality" not in source
