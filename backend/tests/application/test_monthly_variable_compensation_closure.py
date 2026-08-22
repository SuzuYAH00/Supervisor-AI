from datetime import UTC, date, datetime
from decimal import Decimal

from supervisor_ai.application import DailyWorkStatusFact
from supervisor_ai.application.errors import WorkScheduleIncomplete
from supervisor_ai.application.use_cases import (
    CalculateMonthlyVariableCompensationUseCase,
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
    def __init__(self, incomplete=False):
        self.incomplete = incomplete

    def execute(self, query):
        if self.incomplete:
            raise WorkScheduleIncomplete("npx_pauses")
        return GetMonthlyDelayFactsResult(
            query.competence_month,
            tuple(
                MonthlyDelayCountResult(item, query.competence_month, 2)
                for item in query.collaborator_ids
            ),
        )


def factory(session_factory):
    return lambda: SqlAlchemyUnitOfWork(session_factory)


def prepare(session_factory):
    uow_factory = factory(session_factory)
    RegisterOperationalCollaboratorProfileUseCase(uow_factory).execute(
        RegisterOperationalCollaboratorProfileCommand(
            "operator-1", CsatCompetitiveChannel.CHAT
        )
    )
    with uow_factory() as uow:
        for month in (date(2026, 7, 1), date(2026, 8, 1)):
            for day in range(1, 21):
                uow.daily_work_statuses.add(
                    DailyWorkStatusFact(
                        f"{month}-{day}",
                        "operator-1",
                        date(month.year, month.month, day),
                        month,
                        "P",
                        "attendance_sheet",
                        f"{month}:{day}",
                        "sheet",
                        f"A{day}",
                        NOW,
                    )
                )
        uow.commit()
    return uow_factory


def service(session_factory, *, incomplete=False):
    uow_factory = prepare(session_factory)
    csat, recurrence, delays = (
        CsatProvider(),
        RecurrenceProvider(),
        DelayProvider(incomplete),
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
