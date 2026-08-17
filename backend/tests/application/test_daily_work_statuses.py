from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import (
    CollaboratorExternalIdentityNotFound,
    DailyWorkStatusConflict,
)
from supervisor_ai.application.use_cases import (
    DailyWorkStatusInput,
    GetMonthlyPresenceQuery,
    GetMonthlyPresenceUseCase,
    ImportDailyWorkStatusesCommand,
    ImportDailyWorkStatusesUseCase,
    RegisterCollaboratorExternalIdentityCommand,
    RegisterCollaboratorExternalIdentityUseCase,
    RegisterOperationalCollaboratorProfileCommand,
    RegisterOperationalCollaboratorProfileUseCase,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel

NOW = datetime(2026, 8, 17, tzinfo=UTC)


def _prepare_identity(session_factory: sessionmaker[Session]) -> None:
    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    RegisterOperationalCollaboratorProfileUseCase(factory).execute(
        RegisterOperationalCollaboratorProfileCommand(
            "collaborator-1", CsatCompetitiveChannel.CHAT
        )
    )
    RegisterCollaboratorExternalIdentityUseCase(factory).execute(
        RegisterCollaboratorExternalIdentityCommand(
            collaborator_id="collaborator-1",
            source="attendance_sheet",
            external_identity="Agent One",
        )
    )


def _input(*, code: str = "P", identity: str = "Agent One") -> DailyWorkStatusInput:
    return DailyWorkStatusInput(
        fact_id="daily-work-1",
        external_identity=identity,
        work_date=date(2026, 8, 1),
        competence_month=date(2026, 8, 1),
        raw_code=code,
        source="attendance_sheet",
        external_reference="ESCALA - AGOSTO 2026!B11",
        source_sheet="ESCALA - AGOSTO 2026",
        source_cell="B11",
    )


def _importer(
    session_factory: sessionmaker[Session],
) -> ImportDailyWorkStatusesUseCase:
    return ImportDailyWorkStatusesUseCase(
        lambda: SqlAlchemyUnitOfWork(session_factory), lambda: NOW
    )


def test_import_resolves_exact_alias_and_is_idempotent(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare_identity(session_factory)
    command = ImportDailyWorkStatusesCommand((_input(),))

    first = _importer(session_factory).execute(command)
    second = _importer(session_factory).execute(command)

    assert (first.created_count, first.already_existing_count) == (1, 0)
    assert (second.created_count, second.already_existing_count) == (0, 1)
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        facts = unit_of_work.daily_work_statuses.search_month(
            collaborator_id="collaborator-1", competence_month=date(2026, 8, 1)
        )
    assert len(facts) == 1
    assert facts[0].collaborator_id == "collaborator-1"


def test_missing_alias_is_not_matched_by_similarity(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare_identity(session_factory)

    with pytest.raises(CollaboratorExternalIdentityNotFound, match="A11"):
        _importer(session_factory).execute(
            ImportDailyWorkStatusesCommand((_input(identity="AgentOne"),))
        )


def test_missing_alias_rolls_back_other_facts_in_same_import(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare_identity(session_factory)
    unmapped = DailyWorkStatusInput(
        fact_id="daily-work-2",
        external_identity="Unknown Agent",
        work_date=date(2026, 8, 2),
        competence_month=date(2026, 8, 1),
        raw_code="P",
        source="attendance_sheet",
        external_reference="ESCALA - AGOSTO 2026!C11",
        source_sheet="ESCALA - AGOSTO 2026",
        source_cell="C11",
    )

    with pytest.raises(CollaboratorExternalIdentityNotFound):
        _importer(session_factory).execute(
            ImportDailyWorkStatusesCommand((_input(), unmapped))
        )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.daily_work_statuses.search_month(
            collaborator_id="collaborator-1", competence_month=date(2026, 8, 1)
        ) == ()


def test_changed_fact_conflicts_without_overwriting(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare_identity(session_factory)
    _importer(session_factory).execute(ImportDailyWorkStatusesCommand((_input(),)))

    with pytest.raises(DailyWorkStatusConflict):
        _importer(session_factory).execute(
            ImportDailyWorkStatusesCommand((_input(code="F"),))
        )

    summary = GetMonthlyPresenceUseCase(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    ).execute(GetMonthlyPresenceQuery("collaborator-1", date(2026, 8, 1)))
    assert summary.worked_days == 1
    assert summary.penalizable_absence_days == 0


def test_monthly_query_counts_facts_without_using_legacy_totals(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare_identity(session_factory)
    items = tuple(
        DailyWorkStatusInput(
            fact_id=f"daily-work-{index}",
            external_identity="Agent One",
            work_date=date(2026, 8, index),
            competence_month=date(2026, 8, 1),
            raw_code=code,
            source="attendance_sheet",
            external_reference=f"ESCALA - AGOSTO 2026!B{index}",
            source_sheet="ESCALA - AGOSTO 2026",
            source_cell=f"B{index}",
        )
        for index, code in enumerate(("P", "A", "B.H", "OF"), start=1)
    )
    _importer(session_factory).execute(ImportDailyWorkStatusesCommand(items))

    result = GetMonthlyPresenceUseCase(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    ).execute(GetMonthlyPresenceQuery("collaborator-1", date(2026, 8, 1)))

    assert result.worked_days == 1
    assert result.penalizable_absence_days == 2
    assert result.non_penalizable_absence_days == 1
    assert not result.meets_minimum_worked_days
