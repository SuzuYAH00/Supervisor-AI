from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from enum import StrEnum

from supervisor_ai.application.errors import (
    IngestionCoverageUnknown,
    WorkScheduleIncomplete,
)
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.application.use_cases.calculate_monthly_variable_compensation import (  # noqa: E501
    CalculateMonthlyVariableCompensationCommand,
    CalculateMonthlyVariableCompensationUseCase,
    CsatCompetitiveFact,
    MonthlyDelayCountFact,
    RecurrenceCompetitiveFact,
)
from supervisor_ai.application.use_cases.get_monthly_csat_facts import (
    GetMonthlyCsatFactsQuery,
    GetMonthlyCsatFactsUseCase,
)
from supervisor_ai.application.use_cases.get_monthly_recurrence_facts import (
    GetMonthlyRecurrenceFactsQuery,
    GetMonthlyRecurrenceFactsUseCase,
    MonthlyRecurrenceFact,
)
from supervisor_ai.application.use_cases.npx_delays import (
    GetMonthlyDelayFactsFromCoverageUseCase,
    GetMonthlyDelayFactsQuery,
)
from supervisor_ai.rules_engine import (
    CHAT_MINIMUM_RESPONSE_RATE,
    PHONE_MINIMUM_RESPONSE_RATE,
    RECURRENCE_MAXIMUM_POPULATION_AVERAGE,
    CsatCompetitiveChannel,
    MonthlyVariableCompensationStatus,
    VariableCompensationComponentResult,
)


class ClosureStatus(StrEnum):
    CALCULATED = "calculated"
    INCOMPLETE = "incomplete"


class ClosureIssueComponent(StrEnum):
    PRESENCE = "presence"
    CSAT = "csat"
    RECURRENCE = "recurrence"
    DELAYS = "delays"
    WORK_SCHEDULE = "work_schedule"


class ClosureIssueScope(StrEnum):
    COLLABORATOR = "collaborator"
    COMPETENCE = "competence"


class ClosureIssueSeverity(StrEnum):
    BLOCKING = "blocking"


@dataclass(frozen=True, slots=True)
class ClosurePendingIssue:
    code: str
    component: ClosureIssueComponent
    scope: ClosureIssueScope
    competence_month: date
    message: str
    severity: ClosureIssueSeverity
    collaborator_id: str | None = None
    affected_collaborator_ids: tuple[str, ...] = ()
    action_type: str | None = None
    action_target: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class GetMonthlyVariableCompensationClosureQuery:
    competence_month: date
    collaborator_id: str | None = None
    status: ClosureStatus | None = None

    def __post_init__(self) -> None:
        if self.competence_month.day != 1:
            raise ValueError("competence_month must be the first day of a month")
        if self.collaborator_id is not None and not self.collaborator_id.strip():
            raise ValueError("collaborator_id must not be blank")


@dataclass(frozen=True, slots=True)
class ClosureComponent:
    status: str
    reference_month: date
    eligible: bool
    tier: str | None
    amount: Decimal | None
    individual_value: Decimal | None
    team_average: Decimal | None


@dataclass(frozen=True, slots=True)
class CsatClosureComponent:
    result: ClosureComponent
    modality: str
    eligible_contact_count: int
    valid_response_count: int
    raw_average: Decimal | None
    response_rate: Decimal | None
    minimum_response_rate: Decimal


@dataclass(frozen=True, slots=True)
class RecurrenceClosureComponent:
    result: ClosureComponent
    eligible_attendance_count: int
    recurrence_count: int
    team_average_cap_passed: bool | None


@dataclass(frozen=True, slots=True)
class DeductionClosureComponent:
    count: int | None
    amount: Decimal | None


@dataclass(frozen=True, slots=True)
class MonthlyVariableCompensationClosureItem:
    collaborator_id: str
    display_name: str
    competence_month: date
    status: ClosureStatus
    pending_reasons: tuple[str, ...]
    pending_issues: tuple[ClosurePendingIssue, ...]
    current_worked_days: int
    previous_worked_days: int
    csat: CsatClosureComponent
    recurrence: RecurrenceClosureComponent
    delays: DeductionClosureComponent
    absences: DeductionClosureComponent
    positive_amount: Decimal | None
    deductions_amount: Decimal | None
    total_amount: Decimal | None
    flag: str | None


@dataclass(frozen=True, slots=True)
class GetMonthlyVariableCompensationClosureResult:
    competence_month: date
    collaborator_count: int
    calculated_count: int
    incomplete_count: int
    projected_total: Decimal | None
    items: tuple[MonthlyVariableCompensationClosureItem, ...]
    issues: tuple[ClosurePendingIssue, ...] = ()


class GetMonthlyVariableCompensationClosureUseCase:
    """Explica a composição existente sem reproduzir suas regras monetárias."""

    def __init__(
        self,
        factory: UnitOfWorkFactory,
        calculator: CalculateMonthlyVariableCompensationUseCase,
        csat: GetMonthlyCsatFactsUseCase,
        recurrence: GetMonthlyRecurrenceFactsUseCase,
        delays: GetMonthlyDelayFactsFromCoverageUseCase,
    ) -> None:
        self._factory = factory
        self._calculator = calculator
        self._csat = csat
        self._recurrence = recurrence
        self._delays = delays

    def execute(
        self, query: GetMonthlyVariableCompensationClosureQuery
    ) -> GetMonthlyVariableCompensationClosureResult:
        with self._factory() as uow:
            profiles = uow.operational_collaborators.list_all()
        collaborator_ids = tuple(
            item.collaborator_id
            for item in profiles
            if query.collaborator_id is None
            or item.collaborator_id == query.collaborator_id
        )
        if not collaborator_ids:
            return GetMonthlyVariableCompensationClosureResult(
                query.competence_month, 0, 0, 0, Decimal("0.00"), ()
            )
        previous_month = _previous_month(query.competence_month)
        csat_result = self._csat.execute(
            GetMonthlyCsatFactsQuery(query.competence_month, collaborator_ids)
        )
        global_issues: list[ClosurePendingIssue] = []
        recurrence_items: tuple[MonthlyRecurrenceFact, ...]
        try:
            recurrence_items = self._recurrence.execute(
                GetMonthlyRecurrenceFactsQuery(previous_month, collaborator_ids)
            ).items
        except IngestionCoverageUnknown:
            global_issues.append(
                _competence_issue(
                    "recurrence_coverage_missing",
                    ClosureIssueComponent.RECURRENCE,
                    query.competence_month,
                    "A Reincidência não pode ser calculada porque não existe "
                    "cobertura registrada para a fonte MK.",
                    collaborator_ids,
                    "review_recurrence_import",
                    "/imports",
                    (("import_type", "recurrence_mk"),),
                )
            )
            recurrence_items = _empty_recurrence(previous_month, collaborator_ids)
        except ValueError as error:
            if str(error) != "the cohort observation window is incomplete":
                raise
            global_issues.append(
                _competence_issue(
                    "recurrence_coverage_incomplete",
                    ClosureIssueComponent.RECURRENCE,
                    query.competence_month,
                    "A janela de observação da Reincidência ainda não possui "
                    "cobertura completa.",
                    collaborator_ids,
                    "review_recurrence_import",
                    "/imports",
                    (("import_type", "recurrence_mk"),),
                )
            )
            recurrence_items = _empty_recurrence(previous_month, collaborator_ids)
        delay_counts: dict[str, int] = {}
        try:
            delay_counts = {
                item.collaborator_id: item.delay_count
                for item in self._delays.execute(
                    GetMonthlyDelayFactsQuery(query.competence_month, collaborator_ids)
                ).items
            }
        except WorkScheduleIncomplete as error:
            global_issues.append(
                _delay_issue(str(error), query.competence_month, collaborator_ids)
            )
        calculation = self._calculator.execute(
            CalculateMonthlyVariableCompensationCommand(
                query.competence_month,
                collaborator_ids,
                delay_facts=tuple(
                    MonthlyDelayCountFact(
                        item, query.competence_month, delay_counts.get(item, 0)
                    )
                    for item in collaborator_ids
                ),
                csat_facts=tuple(
                    CsatCompetitiveFact(
                        item.collaborator_id,
                        item.reference_month,
                        item.competitive_score,
                        item.response_rate,
                    )
                    for item in csat_result.items
                ),
                recurrence_facts=tuple(
                    RecurrenceCompetitiveFact(
                        item.collaborator_id,
                        item.cohort_month,
                        item.recurrence_rate,
                    )
                    for item in recurrence_items
                ),
            )
        )
        csat_by_id = {item.collaborator_id: item for item in csat_result.items}
        recurrence_by_id = {item.collaborator_id: item for item in recurrence_items}
        inputs = {item.collaborator_id: item for item in calculation.resolved_inputs}
        results = {item.collaborator_id: item for item in calculation.items}
        previous_presence = dict(calculation.previous_presence)
        current_presence_counts = dict(calculation.current_presence_fact_counts)
        previous_presence_counts = dict(calculation.previous_presence_fact_counts)
        items = tuple(
            self._item(
                collaborator_id,
                csat_by_id[collaborator_id],
                recurrence_by_id[collaborator_id],
                inputs[collaborator_id],
                results[collaborator_id],
                delay_counts.get(collaborator_id),
                tuple(global_issues),
                previous_presence[collaborator_id].worked_days,
                current_presence_counts[collaborator_id],
                previous_presence_counts[collaborator_id],
            )
            for collaborator_id in collaborator_ids
        )
        filtered = tuple(
            item
            for item in items
            if query.status is None or item.status is query.status
        )
        calculated_count = sum(
            item.status is ClosureStatus.CALCULATED for item in items
        )
        total = (
            sum((item.total_amount for item in items), start=Decimal("0"))
            if calculated_count == len(items)
            else None
        )
        return GetMonthlyVariableCompensationClosureResult(
            query.competence_month,
            len(items),
            calculated_count,
            len(items) - calculated_count,
            total,
            filtered,
            _aggregate_issues(items),
        )

    def _item(
        self,
        collaborator_id,
        csat,
        recurrence,
        facts,
        result,
        delay_count,
        global_issues,
        previous_worked_days,
        current_presence_fact_count,
        previous_presence_fact_count,
    ):
        issues = [
            issue
            for issue in global_issues
            if (
                issue.scope is ClosureIssueScope.COMPETENCE
                or issue.collaborator_id == collaborator_id
            )
            and (
                issue.component is not ClosureIssueComponent.RECURRENCE
                or facts.recurrence.is_eligible
            )
        ]
        if current_presence_fact_count == 0:
            issues.append(
                _collaborator_issue(
                    "presence_current_month_missing",
                    ClosureIssueComponent.PRESENCE,
                    result.competence.competence_month,
                    collaborator_id,
                    "Não existem fatos de presença para o colaborador nesta "
                    "competência.",
                    "review_attendance_import",
                    "/imports",
                    (("import_type", "workforce_schedule"),),
                )
            )
        if previous_presence_fact_count == 0:
            issues.append(
                _collaborator_issue(
                    "presence_previous_month_missing",
                    ClosureIssueComponent.PRESENCE,
                    result.competence.competence_month,
                    collaborator_id,
                    "Não existem fatos de presença no mês anterior, necessários "
                    "para a elegibilidade da Reincidência.",
                    "review_attendance_import",
                    "/imports",
                    (("import_type", "workforce_schedule"),),
                )
            )
        if result.csat.status.value == "not_evaluable":
            code = (
                "csat_no_eligible_contacts"
                if csat.eligible_contact_count == 0
                else "csat_not_evaluable"
            )
            issues.append(
                _collaborator_issue(
                    code,
                    ClosureIssueComponent.CSAT,
                    result.competence.competence_month,
                    collaborator_id,
                    "O CSAT não possui dados suficientes para calcular o indicador "
                    "do colaborador.",
                    "review_csat_import",
                    "/imports",
                    (
                        (
                            "import_type",
                            "csat_chat_mk"
                            if facts.csat.channel is CsatCompetitiveChannel.CHAT
                            else "csat_phone_npx",
                        ),
                    ),
                )
            )
        if result.recurrence.status.value == "not_evaluable" and not any(
            issue.component is ClosureIssueComponent.RECURRENCE for issue in issues
        ):
            issues.append(
                _collaborator_issue(
                    "recurrence_not_evaluable",
                    ClosureIssueComponent.RECURRENCE,
                    result.competence.competence_month,
                    collaborator_id,
                    "A Reincidência não possui população suficiente para calcular "
                    "a taxa do colaborador.",
                    "review_recurrence_import",
                )
            )
        status = (
            ClosureStatus.CALCULATED
            if result.status is MonthlyVariableCompensationStatus.CALCULATED
            and not issues
            and delay_count is not None
            else ClosureStatus.INCOMPLETE
        )
        csat_result = _component(
            result.csat, facts.csat.operator_score, facts.csat.channel_average
        )
        recurrence_result = _component(
            result.recurrence,
            facts.recurrence.operator_rate,
            facts.recurrence.population_average_rate,
        )
        positive = None
        deductions = None
        if status is ClosureStatus.CALCULATED:
            positive = (result.csat.amount or Decimal("0")) + (
                result.recurrence.amount or Decimal("0")
            )
            deductions = result.delay_discount + result.absence_discount
        return MonthlyVariableCompensationClosureItem(
            collaborator_id,
            collaborator_id,
            result.competence.competence_month,
            status,
            tuple(issue.code for issue in issues),
            tuple(issues),
            facts.csat.worked_days,
            previous_worked_days,
            CsatClosureComponent(
                csat_result,
                facts.csat.channel.value,
                csat.eligible_contact_count,
                csat.valid_response_count,
                csat.raw_average,
                csat.response_rate,
                CHAT_MINIMUM_RESPONSE_RATE
                if facts.csat.channel is CsatCompetitiveChannel.CHAT
                else PHONE_MINIMUM_RESPONSE_RATE,
            ),
            RecurrenceClosureComponent(
                recurrence_result,
                recurrence.eligible_attendance_count,
                recurrence.recurrence_count,
                None
                if facts.recurrence.population_average_rate is None
                else facts.recurrence.population_average_rate
                <= RECURRENCE_MAXIMUM_POPULATION_AVERAGE,
            ),
            DeductionClosureComponent(
                delay_count, result.delay_discount if delay_count is not None else None
            ),
            DeductionClosureComponent(facts.absence_days, result.absence_discount),
            positive,
            deductions,
            result.total_amount if status is ClosureStatus.CALCULATED else None,
            result.flag.value
            if result.flag is not None and status is ClosureStatus.CALCULATED
            else None,
        )


def _component(
    result: VariableCompensationComponentResult,
    individual: Decimal | None,
    average: Decimal | None,
) -> ClosureComponent:
    return ClosureComponent(
        result.status.value,
        result.reference_month,
        result.status.value == "eligible",
        None if result.tier is None else result.tier.value,
        result.amount,
        individual,
        average,
    )


def _empty_recurrence(
    cohort_month: date, collaborator_ids: tuple[str, ...]
) -> tuple[MonthlyRecurrenceFact, ...]:
    return tuple(
        MonthlyRecurrenceFact(item, cohort_month, 0, 0, None)
        for item in collaborator_ids
    )


def _competence_issue(
    code: str,
    component: ClosureIssueComponent,
    competence_month: date,
    message: str,
    collaborator_ids: tuple[str, ...],
    action_type: str | None = None,
    action_target: str | None = None,
    metadata: tuple[tuple[str, str], ...] = (),
) -> ClosurePendingIssue:
    return ClosurePendingIssue(
        code,
        component,
        ClosureIssueScope.COMPETENCE,
        competence_month,
        message,
        ClosureIssueSeverity.BLOCKING,
        affected_collaborator_ids=collaborator_ids,
        action_type=action_type,
        action_target=action_target,
        metadata=metadata,
    )


def _collaborator_issue(
    code: str,
    component: ClosureIssueComponent,
    competence_month: date,
    collaborator_id: str,
    message: str,
    action_type: str | None = None,
    action_target: str | None = None,
    metadata: tuple[tuple[str, str], ...] = (),
) -> ClosurePendingIssue:
    return ClosurePendingIssue(
        code,
        component,
        ClosureIssueScope.COLLABORATOR,
        competence_month,
        message,
        ClosureIssueSeverity.BLOCKING,
        collaborator_id,
        (collaborator_id,),
        action_type,
        action_target,
        metadata,
    )


def _delay_issue(
    reason: str, competence_month: date, collaborator_ids: tuple[str, ...]
) -> ClosurePendingIssue:
    coverage_prefix = "coverage is incomplete for "
    unresolved_prefix = "planned schedule unresolved for "
    if reason.startswith(coverage_prefix):
        dataset = reason.removeprefix(coverage_prefix).split(" through ", 1)[0]
        if dataset == "planned_work_schedules":
            return _competence_issue(
                "work_schedule_coverage_incomplete",
                ClosureIssueComponent.WORK_SCHEDULE,
                competence_month,
                "A Escala não possui cobertura completa para a competência.",
                collaborator_ids,
                "resolve_work_schedules",
                "/work-schedules",
            )
        return _competence_issue(
            f"{dataset}_coverage_incomplete",
            ClosureIssueComponent.DELAYS,
            competence_month,
            "Os atrasos não podem ser concluídos porque a cobertura dos "
            "relatórios NPX está incompleta.",
            collaborator_ids,
            "review_npx_import",
            "/imports",
            (("import_type", dataset),),
        )
    if reason.startswith(unresolved_prefix) and " on " in reason:
        identity, work_date = reason.removeprefix(unresolved_prefix).rsplit(" on ", 1)
        return _collaborator_issue(
            "work_schedule_unresolved",
            ClosureIssueComponent.WORK_SCHEDULE,
            competence_month,
            identity,
            f"A jornada planejada de {work_date} não foi resolvida.",
            "resolve_work_schedule",
            "/work-schedules",
            (("work_date", work_date),),
        )
    raise ValueError(f"unclassified work schedule incompleteness: {reason}")


def _aggregate_issues(
    items: tuple[MonthlyVariableCompensationClosureItem, ...],
) -> tuple[ClosurePendingIssue, ...]:
    unique: dict[tuple[str, str | None], ClosurePendingIssue] = {}
    affected: dict[tuple[str, str | None], list[str]] = {}
    for item in items:
        for issue in item.pending_issues:
            key = (
                issue.code,
                issue.collaborator_id
                if issue.scope is ClosureIssueScope.COLLABORATOR
                else None,
            )
            unique.setdefault(key, issue)
            if issue.scope is ClosureIssueScope.COMPETENCE:
                affected.setdefault(key, []).append(item.collaborator_id)
    return tuple(
        replace(issue, affected_collaborator_ids=tuple(affected.get(key, ())))
        if issue.scope is ClosureIssueScope.COMPETENCE
        else issue
        for key, issue in unique.items()
    )


def _previous_month(value: date) -> date:
    return (
        date(value.year - 1, 12, 1)
        if value.month == 1
        else date(value.year, value.month - 1, 1)
    )
