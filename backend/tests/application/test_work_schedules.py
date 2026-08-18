from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import (
    CollaboratorExternalIdentity,
    DailyWorkStatusFact,
    OperationalCollaboratorProfile,
    WorkScheduleConflict,
    WorkScheduleIncomplete,
)
from supervisor_ai.application.use_cases import (
    CalculateMonthlyVariableCompensationCommand,
    CalculateMonthlyVariableCompensationUseCase,
    CollaboratorWorkScheduleInput,
    CsatCompetitiveFact,
    DailyPlannedWorkScheduleInput,
    GetMonthlyDelayFactsFromCoverageUseCase,
    GetMonthlyDelayFactsQuery,
    ImportNpxFactsCommand,
    ImportNpxFactsUseCase,
    ImportWorkSchedulesCommand,
    ImportWorkSchedulesUseCase,
    NpxCoverageDeclaration,
    RecordDailyWorkScheduleOverrideCommand,
    RecordDailyWorkScheduleOverrideUseCase,
    RecurrenceCompetitiveFact,
    WorkSessionInput,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import (
    CsatCompetitiveChannel,
    MonthlyVariableCompensationEvaluator,
)

NOW = datetime(2026, 8, 31, 12, tzinfo=UTC)


def _factory(session_factory: sessionmaker[Session]):
    return lambda: SqlAlchemyUnitOfWork(session_factory)


def _setup(session_factory: sessionmaker[Session]) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.operational_collaborators.add(
            OperationalCollaboratorProfile(
                "collaborator-1", CsatCompetitiveChannel.CHAT, NOW
            )
        )
        uow.collaborator_external_identities.add(
            CollaboratorExternalIdentity(
                "collaborator-1", "attendance_sheet", "Agent One", NOW
            )
        )
        uow.collaborator_external_identities.add(
            CollaboratorExternalIdentity(
                "collaborator-1", "attendance_sheet", "Agent 1", NOW
            )
        )
        uow.collaborator_external_identities.add(
            CollaboratorExternalIdentity(
                "collaborator-1", "npx", "NPX Agent", NOW
            )
        )
        uow.daily_work_statuses.add(
            DailyWorkStatusFact(
                "status-1", "collaborator-1", date(2026, 8, 3),
                date(2026, 8, 1), "P", "attendance_sheet", "status-ref",
                "ESCALA - AGOSTO 2026", "D3", NOW,
            )
        )
        uow.commit()


def _schedule_command(*, start: time = time(8), end: time = time(14)):
    return ImportWorkSchedulesCommand(
        standards=(CollaboratorWorkScheduleInput(
            "Agent One", start, end, date(2026, 8, 1), date(2026, 8, 31),
            "attendance_sheet", "august-standard",
        ),),
        daily_schedules=(DailyPlannedWorkScheduleInput(
            "Agent One", date(2026, 8, 3), start, end, "standard",
            "attendance_sheet", "august-day-3", "ESCALA - AGOSTO 2026", "D3",
        ),),
        covered_through=date(2026, 8, 31),
        import_reference="schedule-export-august",
    )


def test_standard_schedule_is_historical_and_overlap_is_rejected(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    service = ImportWorkSchedulesUseCase(_factory(session_factory), lambda: NOW)
    service.execute(_schedule_command())
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.collaborator_work_schedules.find_for_date(
            collaborator_id="collaborator-1", work_date=date(2026, 8, 3)
        ).standard_start == time(8)

    overlapping = ImportWorkSchedulesCommand(standards=(
        CollaboratorWorkScheduleInput(
            "Agent One", time(16), time(22), date(2026, 8, 15), None,
            "attendance_sheet", "overlap",
        ),
    ))
    with pytest.raises(WorkScheduleConflict, match="overlap"):
        service.execute(overlapping)


def test_override_is_auditable_and_conflict_is_not_silent(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    service = RecordDailyWorkScheduleOverrideUseCase(
        _factory(session_factory), lambda: NOW
    )
    command = RecordDailyWorkScheduleOverrideCommand(
        "override-1", "collaborator-1", date(2026, 8, 3), time(16), time(22),
        "authorized exchange", "supervisor-1",
    )
    assert service.execute(command).created_by == "supervisor-1"
    with pytest.raises(WorkScheduleConflict):
        service.execute(RecordDailyWorkScheduleOverrideCommand(
            "override-2", "collaborator-1", date(2026, 8, 3), time(8), time(14),
            "other", "supervisor-2",
        ))


def test_aliases_resolve_before_standard_fallback_and_explicit_precedence(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    result = ImportWorkSchedulesUseCase(
        _factory(session_factory), lambda: NOW
    ).execute(ImportWorkSchedulesCommand(
        standards=(CollaboratorWorkScheduleInput(
            "Agent One", time(8), time(14), date(2026, 8, 1),
            date(2026, 8, 31), "attendance_sheet", "standard",
        ),),
        daily_schedules=(
            DailyPlannedWorkScheduleInput(
                "Agent 1", date(2026, 8, 3), time(16), time(22), "explicit",
                "attendance_sheet", "explicit", "WEEKEND", "D5",
            ),
            DailyPlannedWorkScheduleInput(
                "Agent One", date(2026, 8, 3), None, None, "unresolved",
                "attendance_sheet", "main", "ESCALA", "D3",
                "standard_schedule_not_found",
            ),
        ),
    ))
    assert result.created_daily_schedules == 1
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        fact = uow.daily_planned_work_schedules.get_by_collaborator_date(
            collaborator_id="collaborator-1", work_date=date(2026, 8, 3)
        )
        assert (fact.planned_start, fact.planned_end) == (time(16), time(22))


@pytest.mark.parametrize(
    ("login", "expected"),
    [(time(8), 0), (time(8, 0, 59), 0), (time(8, 1), 1), (time(8, 40), 1)],
)
def test_entry_delay_uses_first_login_and_exact_minute_boundary(
    session_factory: sessionmaker[Session], login: time, expected: int
) -> None:
    _setup(session_factory)
    factory = _factory(session_factory)
    ImportWorkSchedulesUseCase(factory, lambda: NOW).execute(_schedule_command())
    local = datetime.combine(date(2026, 8, 3), login).replace(
        tzinfo=ZoneInfo("America/Fortaleza")
    )
    first = WorkSessionInput(
        "session-1", "session-ref-1", "NPX Agent", "1", "Support",
        local, local + timedelta(hours=6), 21600, "npx-august", "Sheet1", 3,
    )
    later = WorkSessionInput(
        "session-2", "session-ref-2", "NPX Agent", "1", "Support",
        local + timedelta(hours=1), local + timedelta(hours=2), 3600,
        "npx-august", "Sheet1", 4,
    )
    coverage = NpxCoverageDeclaration(date(2026, 8, 31), "npx-august")
    ImportNpxFactsUseCase(factory, lambda: NOW).execute(ImportNpxFactsCommand(
        work_sessions=(first, later), work_session_coverage=coverage,
        pause_coverage=coverage,
    ))
    result = GetMonthlyDelayFactsFromCoverageUseCase(factory, lambda: NOW).execute(
        GetMonthlyDelayFactsQuery(date(2026, 8, 1), ("collaborator-1",))
    )
    assert result.items[0].delay_count == expected


def test_unresolved_schedule_blocks_monthly_zero(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    factory = _factory(session_factory)
    command = _schedule_command()
    unresolved = DailyPlannedWorkScheduleInput(
        "Agent One", date(2026, 8, 3), None, None, "unresolved",
        "attendance_sheet", "august-day-3", "ESCALA - AGOSTO 2026", "D3",
        "explicit_schedule_not_found",
    )
    ImportWorkSchedulesUseCase(factory, lambda: NOW).execute(
        ImportWorkSchedulesCommand(command.standards, (unresolved,),
            command.covered_through, command.import_reference)
    )
    coverage = NpxCoverageDeclaration(date(2026, 8, 31), "npx-august")
    ImportNpxFactsUseCase(factory, lambda: NOW).execute(ImportNpxFactsCommand(
        work_session_coverage=coverage, pause_coverage=coverage,
    ))
    with pytest.raises(WorkScheduleIncomplete, match="unresolved"):
        GetMonthlyDelayFactsFromCoverageUseCase(factory, lambda: NOW).execute(
            GetMonthlyDelayFactsQuery(date(2026, 8, 1), ("collaborator-1",))
        )


def test_rv_derives_delay_facts_and_preserves_negative_result(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    factory = _factory(session_factory)
    ImportWorkSchedulesUseCase(factory, lambda: NOW).execute(_schedule_command())
    local = datetime(2026, 8, 3, 8, 1, tzinfo=ZoneInfo("America/Fortaleza"))
    coverage = NpxCoverageDeclaration(date(2026, 8, 31), "npx-august")
    ImportNpxFactsUseCase(factory, lambda: NOW).execute(ImportNpxFactsCommand(
        work_sessions=(WorkSessionInput(
            "session-rv", "session-rv-ref", "NPX Agent", "1", "Support", local,
            local + timedelta(hours=6), 21600, "npx-august", "Sheet1", 3,
        ),),
        work_session_coverage=coverage,
        pause_coverage=coverage,
    ))
    service = CalculateMonthlyVariableCompensationUseCase(
        factory,
        MonthlyVariableCompensationEvaluator(),
        monthly_delay_facts=GetMonthlyDelayFactsFromCoverageUseCase(
            factory, lambda: NOW
        ),
    )
    result = service.execute(CalculateMonthlyVariableCompensationCommand(
        competence_month=date(2026, 8, 1),
        collaborator_ids=("collaborator-1",),
        csat_facts=(CsatCompetitiveFact(
            "collaborator-1", date(2026, 8, 1), None, None
        ),),
        recurrence_facts=(RecurrenceCompetitiveFact(
            "collaborator-1", date(2026, 7, 1), None
        ),),
    ))
    assert result.items[0].delay_discount < 0
    assert result.items[0].total_amount is not None
    assert result.items[0].total_amount < 0
