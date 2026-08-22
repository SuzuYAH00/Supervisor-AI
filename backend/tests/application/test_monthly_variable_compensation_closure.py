from datetime import UTC, date, datetime
from decimal import Decimal

from supervisor_ai.application import DailyWorkStatusFact
from supervisor_ai.application.errors import WorkScheduleIncomplete
from supervisor_ai.application.use_cases import (
    CalculateMonthlyVariableCompensationUseCase,
    ClosureIssueComponent,
    ClosureIssueScope,
    ClosureStatus,
    GetMonthlyCsatFactsResult,
    GetMonthlyDelayFactsResult,
    GetMonthlyRecurrenceFactsResult,
    GetMonthlyVariableCompensationClosureQuery,
    GetMonthlyVariableCompensationClosureUseCase,
    MonthlyCsatFact,
    MonthlyDelayCountResult,
    MonthlyRecurrenceFact,
    RegisterOperationalCollaboratorProfileCommand,
    RegisterOperationalCollaboratorProfileUseCase,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import (
    CsatCompetitiveChannel,
    MonthlyVariableCompensationEvaluator,
)

NOW = datetime(2026, 8, 1, tzinfo=UTC)


class CsatProvider:
    def execute(self, query):
        return GetMonthlyCsatFactsResult(
            query.competence_month,
            tuple(
                MonthlyCsatFact(
                    item,
                    query.competence_month,
                    2,
                    1,
                    Decimal("0.50"),
                    Decimal("4.75"),
                    Decimal("9.50"),
                )
                for item in query.collaborator_ids
            ),
        )


class RecurrenceProvider:
    def execute(self, query):
        return GetMonthlyRecurrenceFactsResult(
            query.cohort_month,
            tuple(
                MonthlyRecurrenceFact(item, query.cohort_month, 10, 1, Decimal("0.10"))
                for item in query.collaborator_ids
            ),
        )


class DelayProvider:
    def __init__(self, incomplete=False, reason=None):
        self.incomplete = incomplete
        self.reason = reason

    def execute(self, query):
        if self.incomplete:
            raise WorkScheduleIncomplete(
                self.reason
                or "coverage is incomplete for npx_pauses through 2026-08-31"
            )
        return GetMonthlyDelayFactsResult(
            query.competence_month,
            tuple(
                MonthlyDelayCountResult(item, query.competence_month, 2)
                for item in query.collaborator_ids
            ),
        )


def factory(session_factory):
    return lambda: SqlAlchemyUnitOfWork(session_factory)


def prepare(
    session_factory,
    collaborator_ids=("operator-1",),
    *,
    with_presence=True,
    delay_reason=None,
):
    uow_factory = factory(session_factory)
    for collaborator_id in collaborator_ids:
        RegisterOperationalCollaboratorProfileUseCase(uow_factory).execute(
            RegisterOperationalCollaboratorProfileCommand(
                collaborator_id, CsatCompetitiveChannel.CHAT
            )
        )
    if not with_presence:
        return uow_factory
    with uow_factory() as uow:
        for collaborator_id in collaborator_ids:
            for month in (date(2026, 7, 1), date(2026, 8, 1)):
                for day in range(1, 21):
                    uow.daily_work_statuses.add(
                        DailyWorkStatusFact(
                            f"{collaborator_id}-{month}-{day}",
                            collaborator_id,
                            date(month.year, month.month, day),
                            month,
                            "P",
                            "attendance_sheet",
                            f"{collaborator_id}:{month}:{day}",
                            "sheet",
                            f"A{day}",
                            NOW,
                        )
                    )
        uow.commit()
    return uow_factory


def service(
    session_factory,
    *,
    incomplete=False,
    collaborator_ids=("operator-1",),
    with_presence=True,
    delay_reason=None,
):
    uow_factory = prepare(
        session_factory, collaborator_ids, with_presence=with_presence
    )
    csat, recurrence, delays = (
        CsatProvider(),
        RecurrenceProvider(),
        DelayProvider(incomplete, delay_reason),
    )
    calculator = CalculateMonthlyVariableCompensationUseCase(
        uow_factory, MonthlyVariableCompensationEvaluator()
    )
    return GetMonthlyVariableCompensationClosureUseCase(
        uow_factory, calculator, csat, recurrence, delays
    )


def test_closure_reuses_calculation_and_explains_components(session_factory):
    result = service(session_factory).execute(
        GetMonthlyVariableCompensationClosureQuery(date(2026, 8, 1))
    )
    item = result.items[0]
    assert item.status is ClosureStatus.CALCULATED
    assert item.csat.result.tier == "gold"
    assert item.delays.count == 2
    assert item.total_amount == Decimal("775.00")
    assert item.recurrence.result.reference_month == date(2026, 7, 1)


def test_incomplete_delay_coverage_never_becomes_zero(session_factory):
    result = service(session_factory, incomplete=True).execute(
        GetMonthlyVariableCompensationClosureQuery(
            date(2026, 8, 1), status=ClosureStatus.INCOMPLETE
        )
    )
    item = result.items[0]
    assert item.status is ClosureStatus.INCOMPLETE
    assert item.delays.count is None
    assert item.total_amount is None
    assert result.projected_total is None
    assert len(result.issues) == 1
    assert result.issues[0].code == "npx_pauses_coverage_incomplete"
    assert result.issues[0].component is ClosureIssueComponent.DELAYS
    assert result.issues[0].scope is ClosureIssueScope.COMPETENCE
    assert result.issues[0].affected_collaborator_ids == ("operator-1",)
    assert result.issues[0].action_target == "/imports"
    assert dict(result.issues[0].metadata) == {"import_type": "npx_pauses"}


def test_global_coverage_issue_is_aggregated_once(session_factory):
    result = service(
        session_factory,
        incomplete=True,
        collaborator_ids=("operator-1", "operator-2"),
    ).execute(GetMonthlyVariableCompensationClosureQuery(date(2026, 8, 1)))

    assert len(result.issues) == 1
    assert result.issues[0].scope is ClosureIssueScope.COMPETENCE
    assert result.issues[0].affected_collaborator_ids == (
        "operator-1",
        "operator-2",
    )


def test_missing_presence_is_individual_and_not_ineligibility(session_factory):
    result = service(session_factory, with_presence=False).execute(
        GetMonthlyVariableCompensationClosureQuery(date(2026, 8, 1))
    )

    assert {issue.code for issue in result.issues} == {
        "presence_current_month_missing",
        "presence_previous_month_missing",
    }
    assert all(
        issue.component is ClosureIssueComponent.PRESENCE for issue in result.issues
    )
    assert all(
        issue.scope is ClosureIssueScope.COLLABORATOR for issue in result.issues
    )


def test_unresolved_schedule_has_individual_action(session_factory):
    result = service(
        session_factory,
        incomplete=True,
        delay_reason="planned schedule unresolved for operator-1 on 2026-08-18",
    ).execute(GetMonthlyVariableCompensationClosureQuery(date(2026, 8, 1)))

    issue = result.issues[0]
    assert issue.code == "work_schedule_unresolved"
    assert issue.component is ClosureIssueComponent.WORK_SCHEDULE
    assert issue.collaborator_id == "operator-1"
    assert issue.action_target == "/work-schedules"
    assert dict(issue.metadata) == {"work_date": "2026-08-18"}
