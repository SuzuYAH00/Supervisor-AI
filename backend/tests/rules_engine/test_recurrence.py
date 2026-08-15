from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from supervisor_ai.rules_engine import (
    ClassificationIdentity,
    RecurrenceAttendance,
    find_recurrences,
    is_recurrence_eligible,
    recurrence_rate,
)

VALID_OPENING = ClassificationIdentity("001", "Sem acesso a internet")
VALID_CLOSING = ClassificationIdentity("001", "Dispositivo Cliente")
VALID_PROCESS = ClassificationIdentity("01", "Atendimento Suporte")


def attendance(
    attendance_id: str,
    *,
    customer: str = "customer-1",
    operator: str = "operator-1",
    channel: str = "phone",
    occurred_at: datetime = datetime(2026, 7, 1, 9, tzinfo=UTC),
    process: ClassificationIdentity = VALID_PROCESS,
    opening: ClassificationIdentity = VALID_OPENING,
    closing: ClassificationIdentity = VALID_CLOSING,
) -> RecurrenceAttendance:
    return RecurrenceAttendance(
        attendance_id=attendance_id,
        customer_code=customer,
        operator_id=operator,
        channel=channel,
        occurred_at=occurred_at,
        process=process,
        opening_classification=opening,
        closing_classification=closing,
    )


@pytest.mark.parametrize(
    ("process", "opening", "closing", "expected"),
    [
        (VALID_PROCESS, VALID_OPENING, VALID_CLOSING, True),
        (
            VALID_PROCESS,
            ClassificationIdentity("999", "Outra abertura"),
            VALID_CLOSING,
            False,
        ),
        (
            VALID_PROCESS,
            VALID_OPENING,
            ClassificationIdentity("014", "Orientação Desbloqueio"),
            False,
        ),
        (
            ClassificationIdentity("02", "Outro processo"),
            VALID_OPENING,
            VALID_CLOSING,
            False,
        ),
    ],
)
def test_eligibility_requires_all_three_dimensions(
    process: ClassificationIdentity,
    opening: ClassificationIdentity,
    closing: ClassificationIdentity,
    expected: bool,
) -> None:
    assert (
        is_recurrence_eligible(
            attendance(
                "attendance-1",
                process=process,
                opening=opening,
                closing=closing,
            )
        )
        is expected
    )


def test_code_and_description_together_define_classification_identity() -> None:
    valid = attendance(
        "valid",
        opening=ClassificationIdentity("014", "Mudança de Endereço"),
    )
    removed = attendance(
        "removed",
        opening=ClassificationIdentity("014", "Problemas em Jogos"),
    )

    assert is_recurrence_eligible(valid)
    assert not is_recurrence_eligible(removed)


@pytest.mark.parametrize(
    ("original_channel", "recurrent_channel"),
    [("phone", "whatsapp"), ("whatsapp", "phone")],
)
def test_channels_do_not_prevent_recurrence(
    original_channel: str, recurrent_channel: str
) -> None:
    original = attendance("a", channel=original_channel)
    recurrent = attendance(
        "b",
        channel=recurrent_channel,
        occurred_at=original.occurred_at + timedelta(days=1),
    )

    assert len(_find(original, recurrent)) == 1


def test_different_customers_do_not_form_recurrence() -> None:
    original = attendance("a", customer="customer-a")
    recurrent = attendance(
        "b",
        customer="customer-b",
        occurred_at=original.occurred_at + timedelta(days=1),
    )

    assert _find(original, recurrent) == ()


@pytest.mark.parametrize(("days", "expected"), [(30, 1), (31, 0)])
def test_window_uses_inclusive_civil_dates(days: int, expected: int) -> None:
    original = attendance("a", occurred_at=datetime(2026, 7, 1, 23, tzinfo=UTC))
    recurrent = attendance(
        "b", occurred_at=datetime(2026, 7, 1, 1, tzinfo=UTC) + timedelta(days=days)
    )

    assert len(_find(original, recurrent)) == expected


def test_chain_links_only_consecutive_eligible_attendances() -> None:
    first = attendance("a", operator="operator-a")
    second = attendance(
        "b", operator="operator-b", occurred_at=first.occurred_at + timedelta(days=2)
    )
    third = attendance(
        "c", operator="operator-c", occurred_at=first.occurred_at + timedelta(days=3)
    )

    result = _find(first, second, third)

    pairs = [
        (item.original_attendance_id, item.recurrent_attendance_id)
        for item in result
    ]
    assert pairs == [
        ("a", "b"),
        ("b", "c"),
    ]
    assert [item.attributed_operator_id for item in result] == [
        "operator-a",
        "operator-b",
    ]


def test_ineligible_contact_between_pair_is_ignored() -> None:
    first = attendance("a")
    ineligible = attendance(
        "ignored",
        occurred_at=first.occurred_at + timedelta(days=1),
        process=ClassificationIdentity("02", "Outro processo"),
    )
    second = attendance("b", occurred_at=first.occurred_at + timedelta(days=2))

    result = _find(first, ineligible, second)

    assert len(result) == 1
    assert result[0].recurrent_attendance_id == "b"


def test_cross_month_return_belongs_to_original_cohort() -> None:
    original = attendance(
        "july",
        operator="july-operator",
        occurred_at=datetime(2026, 7, 31, 23, tzinfo=UTC),
    )
    recurrent = attendance(
        "august", occurred_at=datetime(2026, 8, 1, 1, tzinfo=UTC)
    )

    result = _find(original, recurrent)

    assert len(result) == 1
    assert result[0].original_date == date(2026, 7, 31)
    assert result[0].attributed_operator_id == "july-operator"


def test_rate_uses_only_eligible_attendance_denominator() -> None:
    assert recurrence_rate(5, 43) == Decimal(5) / Decimal(43)
    assert recurrence_rate(0, 0) is None


def _find(*items: RecurrenceAttendance):
    return find_recurrences(
        tuple(items), cohort_start=date(2026, 7, 1), cohort_end=date(2026, 7, 31)
    )
