from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import DailyWorkStatusFact
from supervisor_ai.application.use_cases import (
    CalculateMonthlyVariableCompensationCommand,
    CalculateMonthlyVariableCompensationUseCase,
    CsatCompetitiveFact,
    MonthlyDelayCountFact,
    RecurrenceCompetitiveFact,
    RegisterOperationalCollaboratorProfileCommand,
    RegisterOperationalCollaboratorProfileUseCase,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import (
    CsatCompetitiveChannel,
    MonthlyVariableCompensationEvaluator,
    VariableCompensationComponentStatus,
    VariableCompensationFlag,
    VariableCompensationTier,
)

NOW = datetime(2026, 8, 17, tzinfo=UTC)


def _factory(session_factory: sessionmaker[Session]):
    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    return factory


def _profile(
    session_factory: sessionmaker[Session],
    collaborator_id: str,
    channel: CsatCompetitiveChannel = CsatCompetitiveChannel.CHAT,
) -> None:
    RegisterOperationalCollaboratorProfileUseCase(_factory(session_factory)).execute(
        RegisterOperationalCollaboratorProfileCommand(collaborator_id, channel)
    )


def _presence(
    session_factory: sessionmaker[Session],
    collaborator_id: str,
    month: date,
    codes: tuple[str, ...],
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        for day, code in enumerate(codes, start=1):
            unit_of_work.daily_work_statuses.add(
                DailyWorkStatusFact(
                    id=f"{collaborator_id}-{month.isoformat()}-{day}",
                    collaborator_id=collaborator_id,
                    work_date=date(month.year, month.month, day),
                    competence_month=month,
                    raw_code=code,
                    source="attendance_sheet",
                    external_reference=(
                        f"{collaborator_id}:{month.isoformat()}:{day}"
                    ),
                    source_sheet=f"ESCALA - {month.isoformat()}",
                    source_cell=f"B{day}",
                    created_at=NOW,
                )
            )
        unit_of_work.commit()


def _calculate(
    session_factory: sessionmaker[Session],
    *,
    competence: date,
    collaborators: tuple[str, ...],
    scores: dict[str, str | None],
    response_rates: dict[str, str | None],
    recurrence_rates: dict[str, str | None],
):
    previous = (
        date(competence.year - 1, 12, 1)
        if competence.month == 1
        else date(competence.year, competence.month - 1, 1)
    )
    command = CalculateMonthlyVariableCompensationCommand(
        competence_month=competence,
        collaborator_ids=collaborators,
        csat_facts=tuple(
            CsatCompetitiveFact(
                collaborator_id,
                competence,
                (
                    None
                    if scores[collaborator_id] is None
                    else Decimal(scores[collaborator_id])
                ),
                (
                    None
                    if response_rates[collaborator_id] is None
                    else Decimal(response_rates[collaborator_id])
                ),
            )
            for collaborator_id in collaborators
        ),
        recurrence_facts=tuple(
            RecurrenceCompetitiveFact(
                collaborator_id,
                previous,
                (
                    None
                    if recurrence_rates[collaborator_id] is None
                    else Decimal(recurrence_rates[collaborator_id])
                ),
            )
            for collaborator_id in collaborators
        ),
        delay_facts=tuple(
            MonthlyDelayCountFact(collaborator_id, competence, 0)
            for collaborator_id in collaborators
        ),
    )
    result = CalculateMonthlyVariableCompensationUseCase(
        _factory(session_factory), MonthlyVariableCompensationEvaluator()
    ).execute(command)
    return {item.collaborator_id: item for item in result.items}


def test_csat_population_excludes_presence_ineligible_operator(
    session_factory: sessionmaker[Session],
) -> None:
    collaborators = ("operator-a", "operator-b", "operator-c")
    for collaborator_id in collaborators:
        _profile(session_factory, collaborator_id)
        _presence(
            session_factory,
            collaborator_id,
            date(2026, 8, 1),
            ("P",) * (19 if collaborator_id == "operator-b" else 20),
        )

    result = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=collaborators,
        scores={"operator-a": "9.10", "operator-b": "10", "operator-c": "9.00"},
        response_rates={item: "0.40" for item in collaborators},
        recurrence_rates={item: None for item in collaborators},
    )

    assert result["operator-a"].csat.tier is VariableCompensationTier.BRONZE
    assert result["operator-b"].csat.status is (
        VariableCompensationComponentStatus.NOT_ELIGIBLE
    )


def test_csat_response_requirement_and_profile_channel_are_preserved(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "chat-operator", CsatCompetitiveChannel.CHAT)
    _profile(session_factory, "phone-operator", CsatCompetitiveChannel.PHONE)
    for collaborator_id in ("chat-operator", "phone-operator"):
        _presence(
            session_factory,
            collaborator_id,
            date(2026, 8, 1),
            ("P",) * 20,
        )

    result = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=("chat-operator", "phone-operator"),
        scores={"chat-operator": "10", "phone-operator": "10"},
        response_rates={"chat-operator": "0.39", "phone-operator": "0.50"},
        recurrence_rates={"chat-operator": None, "phone-operator": None},
    )

    assert result["chat-operator"].csat.status is (
        VariableCompensationComponentStatus.NOT_ELIGIBLE
    )
    assert result["phone-operator"].csat.tier is VariableCompensationTier.GOLD


def test_recurrence_uses_previous_month_and_current_absence_discount(
    session_factory: sessionmaker[Session],
) -> None:
    for collaborator_id in ("operator-a", "operator-b"):
        _profile(session_factory, collaborator_id)
        _presence(
            session_factory,
            collaborator_id,
            date(2026, 7, 1),
            ("P",) * 20,
        )
    _presence(session_factory, "operator-a", date(2026, 8, 1), ("A",))

    result = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=("operator-a", "operator-b"),
        scores={"operator-a": None, "operator-b": None},
        response_rates={"operator-a": None, "operator-b": None},
        recurrence_rates={"operator-a": "0.08", "operator-b": "0.20"},
    )["operator-a"]

    assert result.csat.status is VariableCompensationComponentStatus.NOT_ELIGIBLE
    assert result.recurrence.tier is VariableCompensationTier.SILVER
    assert result.recurrence.reference_month == date(2026, 7, 1)
    assert result.absence_discount == Decimal("-50.00")
    assert result.total_amount == Decimal("150.00")


def test_recurrence_population_excludes_prior_month_ineligible_operator(
    session_factory: sessionmaker[Session],
) -> None:
    collaborators = ("operator-a", "operator-b", "operator-c")
    for collaborator_id in collaborators:
        _profile(session_factory, collaborator_id)
        _presence(
            session_factory,
            collaborator_id,
            date(2026, 7, 1),
            ("P",) * (19 if collaborator_id == "operator-b" else 20),
        )

    result = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=collaborators,
        scores={item: None for item in collaborators},
        response_rates={item: None for item in collaborators},
        recurrence_rates={
            "operator-a": "0.08",
            "operator-b": "0.50",
            "operator-c": "0.20",
        },
    )

    assert result["operator-a"].recurrence.tier is VariableCompensationTier.SILVER
    assert result["operator-b"].recurrence.status is (
        VariableCompensationComponentStatus.NOT_ELIGIBLE
    )


def test_recurrence_collective_lock_blocks_every_award(
    session_factory: sessionmaker[Session],
) -> None:
    for collaborator_id in ("operator-a", "operator-b"):
        _profile(session_factory, collaborator_id)
        _presence(
            session_factory,
            collaborator_id,
            date(2026, 7, 1),
            ("P",) * 20,
        )

    result = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=("operator-a", "operator-b"),
        scores={"operator-a": None, "operator-b": None},
        response_rates={"operator-a": None, "operator-b": None},
        recurrence_rates={"operator-a": "0.10", "operator-b": "0.40"},
    )

    assert all(item.recurrence.amount == Decimal("0.00") for item in result.values())


def test_time_bank_is_not_discounted_and_can_prevent_eligibility(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "operator-a")
    _presence(
        session_factory,
        "operator-a",
        date(2026, 8, 1),
        ("P",) * 19 + ("B.H",),
    )

    result = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=("operator-a",),
        scores={"operator-a": "10"},
        response_rates={"operator-a": "1"},
        recurrence_rates={"operator-a": None},
    )["operator-a"]

    assert result.csat.status is VariableCompensationComponentStatus.NOT_ELIGIBLE
    assert result.absence_discount == Decimal("0.00")


@pytest.mark.parametrize(
    ("absence_count", "expected_discount"),
    ((0, "0.00"), (1, "-50.00"), (2, "-75.00"), (3, "-250.00"), (4, "-250.00")),
)
def test_penalizable_absences_from_presence_feed_monthly_discount(
    session_factory: sessionmaker[Session],
    absence_count: int,
    expected_discount: str,
) -> None:
    _profile(session_factory, "operator-a")
    if absence_count:
        _presence(
            session_factory,
            "operator-a",
            date(2026, 8, 1),
            ("A",) * absence_count,
        )

    result = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=("operator-a",),
        scores={"operator-a": None},
        response_rates={"operator-a": None},
        recurrence_rates={"operator-a": None},
    )["operator-a"]

    assert result.absence_discount == Decimal(expected_discount)


def test_full_and_partial_component_compositions_preserve_negative_results(
    session_factory: sessionmaker[Session],
) -> None:
    for collaborator_id in ("both", "helper"):
        _profile(session_factory, collaborator_id)
        _presence(
            session_factory,
            collaborator_id,
            date(2026, 7, 1),
            ("P",) * 20,
        )
        _presence(
            session_factory,
            collaborator_id,
            date(2026, 8, 1),
            ("P",) * 20,
        )
    result = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=("both", "helper"),
        scores={"both": "9.50", "helper": "9.50"},
        response_rates={"both": "1", "helper": "1"},
        recurrence_rates={"both": "0.08", "helper": "0.32"},
    )["both"]
    assert result.total_amount == Decimal("1600.00")

    _profile(session_factory, "neither")
    _presence(
        session_factory,
        "neither",
        date(2026, 8, 1),
        ("P",) * 19 + ("A",),
    )
    _presence(
        session_factory,
        "neither",
        date(2026, 7, 1),
        ("P",) * 19,
    )
    negative = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=("neither",),
        scores={"neither": "10"},
        response_rates={"neither": "1"},
        recurrence_rates={"neither": "0"},
    )["neither"]
    assert negative.total_amount == Decimal("-50.00")
    assert negative.flag is VariableCompensationFlag.RED


def test_each_component_can_remain_eligible_independently(
    session_factory: sessionmaker[Session],
) -> None:
    for collaborator_id in ("csat-only", "recurrence-only", "helper"):
        _profile(session_factory, collaborator_id)
    for collaborator_id in ("csat-only", "helper"):
        _presence(
            session_factory,
            collaborator_id,
            date(2026, 8, 1),
            ("P",) * 20,
        )
    for collaborator_id in ("recurrence-only", "helper"):
        _presence(
            session_factory,
            collaborator_id,
            date(2026, 7, 1),
            ("P",) * 20,
        )

    result = _calculate(
        session_factory,
        competence=date(2026, 8, 1),
        collaborators=("csat-only", "recurrence-only", "helper"),
        scores={"csat-only": "9.50", "recurrence-only": "9.50", "helper": "9.50"},
        response_rates={"csat-only": "1", "recurrence-only": "1", "helper": "1"},
        recurrence_rates={
            "csat-only": "0.08",
            "recurrence-only": "0.08",
            "helper": "0.32",
        },
    )

    assert result["csat-only"].total_amount == Decimal("800.00")
    assert result["csat-only"].recurrence.status is (
        VariableCompensationComponentStatus.NOT_ELIGIBLE
    )
    assert result["recurrence-only"].total_amount == Decimal("800.00")
    assert result["recurrence-only"].csat.status is (
        VariableCompensationComponentStatus.NOT_ELIGIBLE
    )


def test_january_uses_previous_year_december_presence(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "operator-a")
    _presence(
        session_factory,
        "operator-a",
        date(2025, 12, 1),
        ("P",) * 20,
    )

    result = _calculate(
        session_factory,
        competence=date(2026, 1, 1),
        collaborators=("operator-a",),
        scores={"operator-a": None},
        response_rates={"operator-a": None},
        recurrence_rates={"operator-a": "0.10"},
    )["operator-a"]

    assert result.recurrence.status is VariableCompensationComponentStatus.ELIGIBLE
    assert result.recurrence.reference_month == date(2025, 12, 1)
