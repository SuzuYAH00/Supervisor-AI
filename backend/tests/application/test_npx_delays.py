from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application.persistence import (
    CollaboratorExternalIdentity,
    OperationalCollaboratorProfile,
)
from supervisor_ai.application.use_cases.npx_delays import (
    GetMonthlyDelayCountQuery,
    GetMonthlyDelayCountUseCase,
    ImportNpxFactsCommand,
    ImportNpxFactsUseCase,
    NpxCoverageDeclaration,
    PauseInput,
    RecordDelayReviewCommand,
    RecordDelayReviewUseCase,
    WorkSessionInput,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel
from supervisor_ai.rules_engine.delays import DelayDecision

NOW = datetime(2026, 8, 18, 12, tzinfo=UTC)


def _factory(session_factory: sessionmaker[Session]):
    return lambda: SqlAlchemyUnitOfWork(session_factory)


def _setup(session_factory: sessionmaker[Session]) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.operational_collaborators.add(
            OperationalCollaboratorProfile(
                "operator-1", CsatCompetitiveChannel.CHAT, NOW
            )
        )
        uow.collaborator_external_identities.add(
            CollaboratorExternalIdentity("operator-1", "npx", "Agent Test", NOW)
        )
        uow.commit()


def _pause(identity: str = "Agent Test") -> PauseInput:
    start = datetime(2026, 8, 3, 10, tzinfo=UTC)
    return PauseInput(
        "pause-1",
        "npx-pause-1",
        identity,
        "001",
        "Support",
        start,
        start + timedelta(minutes=21),
        1260,
        "extract-1",
        "Sheet1",
        3,
        "Intervalo 20min",
        "NÃO",
    )


def _session() -> WorkSessionInput:
    start = datetime(2026, 8, 3, 8, 40, tzinfo=UTC)
    return WorkSessionInput(
        "session-1",
        "npx-session-1",
        "Agent Test",
        "001",
        "Support",
        start,
        start + timedelta(hours=6),
        21600,
        "extract-1",
        "Sheet1",
        3,
    )


def test_import_is_idempotent_derives_delay_and_records_coverage(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    service = ImportNpxFactsUseCase(_factory(session_factory), lambda: NOW)
    command = ImportNpxFactsCommand(
        pauses=(_pause(),),
        pause_coverage=NpxCoverageDeclaration(date(2026, 8, 31), "extract-1"),
    )
    first = service.execute(command)
    second = service.execute(command)

    assert first.imported_pauses == 1
    assert first.delay_occurrences_created == 1
    assert second.idempotent_rows == 1
    assert second.delay_occurrences_created == 0
    assert (
        GetMonthlyDelayCountUseCase(_factory(session_factory))
        .execute(GetMonthlyDelayCountQuery("operator-1", date(2026, 8, 1)))
        .delay_count
        == 1
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.ingestion_coverages.get_latest(
            dataset="npx_pauses", source="npx"
        ).covered_through == date(2026, 8, 31)


def test_unknown_alias_is_rejected_without_fuzzy_matching(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    result = ImportNpxFactsUseCase(_factory(session_factory), lambda: NOW).execute(
        ImportNpxFactsCommand(pauses=(_pause("Agent  Test"),))
    )
    assert result.rejected_rows == 1
    assert result.issues[0].code == "unknown_collaborator_alias"


def test_work_session_is_persisted_but_does_not_invent_entry_delay(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    service = ImportNpxFactsUseCase(_factory(session_factory), lambda: NOW)
    command = ImportNpxFactsCommand(work_sessions=(_session(),))
    assert service.execute(command).imported_work_sessions == 1
    assert service.execute(command).idempotent_rows == 1
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert (
            len(
                uow.work_sessions.search_date(
                    collaborator_id="operator-1", work_date=date(2026, 8, 3)
                )
            )
            == 1
        )
        assert not uow.delay_occurrences.search_month(
            collaborator_id="operator-1", competence_month=date(2026, 8, 1)
        )


def test_corrected_review_removes_delay_from_count(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    factory = _factory(session_factory)
    ImportNpxFactsUseCase(factory, lambda: NOW).execute(
        ImportNpxFactsCommand(pauses=(_pause(),))
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        occurrence = uow.delay_occurrences.search_month(
            collaborator_id="operator-1", competence_month=date(2026, 8, 1)
        )[0]
    RecordDelayReviewUseCase(factory, lambda: NOW).execute(
        RecordDelayReviewCommand(
            "review-1",
            occurrence.id,
            DelayDecision.CORRECTED,
            NOW,
            "supervisor-1",
        )
    )
    assert (
        GetMonthlyDelayCountUseCase(factory)
        .execute(GetMonthlyDelayCountQuery("operator-1", date(2026, 8, 1)))
        .delay_count
        == 0
    )


def test_valid_review_keeps_delay_countable(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    factory = _factory(session_factory)
    ImportNpxFactsUseCase(factory, lambda: NOW).execute(
        ImportNpxFactsCommand(pauses=(_pause(),))
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        occurrence = uow.delay_occurrences.search_month(
            collaborator_id="operator-1", competence_month=date(2026, 8, 1)
        )[0]
    RecordDelayReviewUseCase(factory, lambda: NOW).execute(
        RecordDelayReviewCommand(
            "review-1", occurrence.id, DelayDecision.VALID, NOW, "supervisor-1"
        )
    )
    assert (
        GetMonthlyDelayCountUseCase(factory)
        .execute(GetMonthlyDelayCountQuery("operator-1", date(2026, 8, 1)))
        .delay_count
        == 1
    )
