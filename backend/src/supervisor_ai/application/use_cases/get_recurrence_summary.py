from dataclasses import dataclass
from decimal import Decimal

from supervisor_ai.application.persistence import AttendanceFact
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.application.recurrence import RecurrenceCohortQuery
from supervisor_ai.rules_engine import (
    RecurrenceAttendance,
    RecurrenceOccurrence,
    find_recurrences,
    is_recurrence_eligible,
    recurrence_rate,
)


@dataclass(frozen=True, slots=True)
class RecurrenceOperatorSummary:
    operator_id: str
    eligible_attendance_count: int
    recurrence_count: int
    recurrence_rate: Decimal | None


@dataclass(frozen=True, slots=True)
class GetRecurrenceSummaryResult:
    query: RecurrenceCohortQuery
    eligible_attendance_count: int
    recurrence_count: int
    recurrence_rate: Decimal | None
    by_operator: tuple[RecurrenceOperatorSummary, ...]
    occurrences: tuple[RecurrenceOccurrence, ...]


class GetRecurrenceSummaryUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, query: RecurrenceCohortQuery
    ) -> GetRecurrenceSummaryResult:
        with self._unit_of_work_factory() as unit_of_work:
            facts = unit_of_work.attendances.search(
                operator_id=None,
                customer_code=None,
                source=None,
                channel=None,
                start_date=query.reference_month,
                end_date=query.window_end,
            )
        recurrence_inputs = tuple(_rule_input(item) for item in facts)
        all_occurrences = find_recurrences(
            recurrence_inputs,
            cohort_start=query.reference_month,
            cohort_end=query.cohort_end,
        )
        original_facts = {
            item.id: item
            for item in facts
            if query.reference_month <= item.occurred_at.date() <= query.cohort_end
            and is_recurrence_eligible(_rule_input(item))
            and _matches_scope(item, query)
        }
        occurrences = tuple(
            item
            for item in all_occurrences
            if item.original_attendance_id in original_facts
        )
        return _result(query, original_facts, occurrences)


def _matches_scope(fact: AttendanceFact, query: RecurrenceCohortQuery) -> bool:
    return all(
        (
            query.operator_id is None or fact.operator_id == query.operator_id,
            query.source is None or fact.source == query.source,
            query.channel is None or fact.channel == query.channel,
        )
    )


def _rule_input(fact: AttendanceFact) -> RecurrenceAttendance:
    return RecurrenceAttendance(
        attendance_id=fact.id,
        customer_code=fact.customer_code,
        operator_id=fact.operator_id,
        channel=fact.channel,
        occurred_at=fact.occurred_at,
        process=fact.process,
        opening_classification=fact.opening_classification,
        closing_classification=fact.closing_classification,
    )


def _result(
    query: RecurrenceCohortQuery,
    original_facts: dict[str, AttendanceFact],
    occurrences: tuple[RecurrenceOccurrence, ...],
) -> GetRecurrenceSummaryResult:
    eligible_by_operator: dict[str, int] = {}
    recurrence_by_operator: dict[str, int] = {}
    for fact in original_facts.values():
        eligible_by_operator[fact.operator_id] = (
            eligible_by_operator.get(fact.operator_id, 0) + 1
        )
    for occurrence in occurrences:
        operator = occurrence.attributed_operator_id
        recurrence_by_operator[operator] = recurrence_by_operator.get(operator, 0) + 1
    groups = tuple(
        RecurrenceOperatorSummary(
            operator_id=operator,
            eligible_attendance_count=count,
            recurrence_count=recurrence_by_operator.get(operator, 0),
            recurrence_rate=recurrence_rate(
                recurrence_by_operator.get(operator, 0), count
            ),
        )
        for operator, count in sorted(eligible_by_operator.items())
    )
    eligible_count = len(original_facts)
    recurrence_count = len(occurrences)
    return GetRecurrenceSummaryResult(
        query=query,
        eligible_attendance_count=eligible_count,
        recurrence_count=recurrence_count,
        recurrence_rate=recurrence_rate(recurrence_count, eligible_count),
        by_operator=groups,
        occurrences=occurrences,
    )
