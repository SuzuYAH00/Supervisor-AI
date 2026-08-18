from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import CsatContact, DailyWorkStatusFact
from supervisor_ai.application.use_cases import (
    CalculateMonthlyVariableCompensationCommand,
    CalculateMonthlyVariableCompensationUseCase,
    GetMonthlyCsatFactsQuery,
    GetMonthlyCsatFactsUseCase,
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
    VariableCompensationTier,
)

NOW = datetime(2026, 8, 18, tzinfo=UTC)


def _factory(session_factory: sessionmaker[Session]):
    return lambda: SqlAlchemyUnitOfWork(session_factory)


def _profile(
    session_factory: sessionmaker[Session],
    collaborator_id: str,
    channel: CsatCompetitiveChannel,
) -> None:
    RegisterOperationalCollaboratorProfileUseCase(_factory(session_factory)).execute(
        RegisterOperationalCollaboratorProfileCommand(collaborator_id, channel)
    )


def _contact(
    session_factory: sessionmaker[Session],
    collaborator_id: str,
    channel: CsatCompetitiveChannel,
    reference: str,
    score: Decimal | None,
    *,
    occurred_on: date = date(2026, 8, 5),
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.csat_contacts.add(
            CsatContact(
                id=f"contact-{reference}",
                external_reference=reference,
                source="mk" if channel is CsatCompetitiveChannel.CHAT else "npx",
                collaborator_id=collaborator_id,
                external_operator_identity=f"external-{collaborator_id}",
                occurred_on=occurred_on,
                source_channel=channel,
                score=score,
                created_at=NOW,
            )
        )
        unit_of_work.commit()


def _presence(
    session_factory: sessionmaker[Session], collaborator_id: str, days: int
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        for day in range(1, days + 1):
            unit_of_work.daily_work_statuses.add(
                DailyWorkStatusFact(
                    id=f"presence-{collaborator_id}-{day}",
                    collaborator_id=collaborator_id,
                    work_date=date(2026, 8, day),
                    competence_month=date(2026, 8, 1),
                    raw_code="P",
                    source="attendance_sheet",
                    external_reference=f"{collaborator_id}:{day}",
                    source_sheet="ESCALA - AGOSTO 2026",
                    source_cell=f"B{day}",
                    created_at=NOW,
                )
            )
        unit_of_work.commit()


def test_monthly_fact_derives_rate_average_and_competitive_score(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "chat-operator", CsatCompetitiveChannel.CHAT)
    for index, score in enumerate((Decimal("4"), Decimal("5"), None, None, None)):
        _contact(
            session_factory,
            "chat-operator",
            CsatCompetitiveChannel.CHAT,
            f"mk-{index}",
            score,
        )

    item = GetMonthlyCsatFactsUseCase(_factory(session_factory)).execute(
        GetMonthlyCsatFactsQuery(date(2026, 8, 1), ("chat-operator",))
    ).items[0]

    assert item.eligible_contact_count == 5
    assert item.valid_response_count == 2
    assert item.response_rate == Decimal("0.4")
    assert item.raw_average == Decimal("4.5")
    assert item.competitive_score == Decimal("9.0")


def test_zero_contacts_is_explicitly_not_evaluable(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "phone-operator", CsatCompetitiveChannel.PHONE)

    item = GetMonthlyCsatFactsUseCase(_factory(session_factory)).execute(
        GetMonthlyCsatFactsQuery(date(2026, 8, 1), ("phone-operator",))
    ).items[0]

    assert item.eligible_contact_count == 0
    assert item.valid_response_count == 0
    assert item.response_rate is None
    assert item.raw_average is None
    assert item.competitive_score is None


def test_profile_channel_selects_population_not_occasional_source_channel(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "chat-operator", CsatCompetitiveChannel.CHAT)
    _contact(
        session_factory,
        "chat-operator",
        CsatCompetitiveChannel.CHAT,
        "mk-contact",
        Decimal("4"),
    )
    _contact(
        session_factory,
        "chat-operator",
        CsatCompetitiveChannel.PHONE,
        "npx-contact",
        Decimal("5"),
    )

    item = GetMonthlyCsatFactsUseCase(_factory(session_factory)).execute(
        GetMonthlyCsatFactsQuery(date(2026, 8, 1), ("chat-operator",))
    ).items[0]

    assert item.eligible_contact_count == 1
    assert item.raw_average == Decimal("4")


def test_contact_date_defines_competence(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "chat-operator", CsatCompetitiveChannel.CHAT)
    _contact(
        session_factory,
        "chat-operator",
        CsatCompetitiveChannel.CHAT,
        "july-contact",
        Decimal("5"),
        occurred_on=date(2026, 7, 31),
    )

    item = GetMonthlyCsatFactsUseCase(_factory(session_factory)).execute(
        GetMonthlyCsatFactsQuery(date(2026, 8, 1), ("chat-operator",))
    ).items[0]

    assert item.eligible_contact_count == 0


def test_rv_automatically_consumes_chat_and_phone_monthly_facts(
    session_factory: sessionmaker[Session],
) -> None:
    collaborators = ("chat-operator", "phone-operator")
    _profile(session_factory, collaborators[0], CsatCompetitiveChannel.CHAT)
    _profile(session_factory, collaborators[1], CsatCompetitiveChannel.PHONE)
    for collaborator_id in collaborators:
        _presence(session_factory, collaborator_id, 20)
    for index, score in enumerate((Decimal("5"), Decimal("5"), None, None, None)):
        _contact(
            session_factory,
            collaborators[0],
            CsatCompetitiveChannel.CHAT,
            f"chat-{index}",
            score,
        )
    for index, score in enumerate((Decimal("5"), None)):
        _contact(
            session_factory,
            collaborators[1],
            CsatCompetitiveChannel.PHONE,
            f"phone-{index}",
            score,
        )
    service = CalculateMonthlyVariableCompensationUseCase(
        _factory(session_factory),
        MonthlyVariableCompensationEvaluator(),
        GetMonthlyCsatFactsUseCase(_factory(session_factory)),
    )

    result = service.execute(
        CalculateMonthlyVariableCompensationCommand(
            competence_month=date(2026, 8, 1),
            collaborator_ids=collaborators,
            recurrence_facts=tuple(
                RecurrenceCompetitiveFact(
                    collaborator_id, date(2026, 7, 1), None
                )
                for collaborator_id in collaborators
            ),
            delay_facts=tuple(
                MonthlyDelayCountFact(collaborator_id, date(2026, 8, 1), 0)
                for collaborator_id in collaborators
            ),
        )
    )
    by_id = {item.collaborator_id: item for item in result.items}

    assert by_id["chat-operator"].csat.tier is VariableCompensationTier.GOLD
    assert by_id["phone-operator"].csat.tier is VariableCompensationTier.GOLD


def test_below_minimum_rate_is_not_eligible_after_automatic_derivation(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "chat-operator", CsatCompetitiveChannel.CHAT)
    _presence(session_factory, "chat-operator", 20)
    for index, score in enumerate((Decimal("5"), None, None)):
        _contact(
            session_factory,
            "chat-operator",
            CsatCompetitiveChannel.CHAT,
            f"contact-{index}",
            score,
        )
    service = CalculateMonthlyVariableCompensationUseCase(
        _factory(session_factory),
        MonthlyVariableCompensationEvaluator(),
        GetMonthlyCsatFactsUseCase(_factory(session_factory)),
    )

    result = service.execute(
        CalculateMonthlyVariableCompensationCommand(
            competence_month=date(2026, 8, 1),
            collaborator_ids=("chat-operator",),
            recurrence_facts=(
                RecurrenceCompetitiveFact(
                    "chat-operator", date(2026, 7, 1), None
                ),
            ),
            delay_facts=(
                MonthlyDelayCountFact(
                    "chat-operator", date(2026, 8, 1), 0
                ),
            ),
        )
    ).items[0]

    assert result.csat.status is VariableCompensationComponentStatus.NOT_ELIGIBLE


def test_team_average_has_equal_operator_weight_not_response_weight(
    session_factory: sessionmaker[Session],
) -> None:
    collaborators = ("operator-a", "operator-b", "operator-c")
    for collaborator_id in collaborators:
        _profile(session_factory, collaborator_id, CsatCompetitiveChannel.CHAT)
        _presence(session_factory, collaborator_id, 20)
    _contact(
        session_factory,
        "operator-a",
        CsatCompetitiveChannel.CHAT,
        "a-1",
        Decimal("5"),
    )
    for index in range(9):
        _contact(
            session_factory,
            "operator-b",
            CsatCompetitiveChannel.CHAT,
            f"b-{index}",
            Decimal("4"),
        )
    _contact(
        session_factory,
        "operator-c",
        CsatCompetitiveChannel.CHAT,
        "c-1",
        Decimal("4.45"),
    )
    service = CalculateMonthlyVariableCompensationUseCase(
        _factory(session_factory),
        MonthlyVariableCompensationEvaluator(),
        GetMonthlyCsatFactsUseCase(_factory(session_factory)),
    )

    result = service.execute(
        CalculateMonthlyVariableCompensationCommand(
            competence_month=date(2026, 8, 1),
            collaborator_ids=collaborators,
            recurrence_facts=tuple(
                RecurrenceCompetitiveFact(
                    collaborator_id, date(2026, 7, 1), None
                )
                for collaborator_id in collaborators
            ),
            delay_facts=tuple(
                MonthlyDelayCountFact(collaborator_id, date(2026, 8, 1), 0)
                for collaborator_id in collaborators
            ),
        )
    )
    operator_c = next(
        item for item in result.items if item.collaborator_id == "operator-c"
    )

    assert operator_c.csat.status is VariableCompensationComponentStatus.ELIGIBLE
    assert operator_c.csat.tier is None
    assert operator_c.csat.amount == Decimal("0.00")
