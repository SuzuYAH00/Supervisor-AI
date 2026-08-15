from datetime import UTC, date, datetime
from types import TracebackType

import pytest

from supervisor_ai.application import (
    AttendanceFact,
    AttendanceFactConflict,
    AttendanceFilters,
    RecurrenceCohortQuery,
)
from supervisor_ai.application.use_cases import (
    AttendanceInput,
    GetAttendancesUseCase,
    GetRecurrenceSummaryUseCase,
    ImportAttendancesCommand,
    ImportAttendancesUseCase,
)
from supervisor_ai.rules_engine import ClassificationIdentity

NOW = datetime(2026, 7, 1, 12, tzinfo=UTC)
PROCESS = ClassificationIdentity("01", "Atendimento Suporte")
OPENING = ClassificationIdentity("001", "Sem acesso a internet")
CLOSING = ClassificationIdentity("001", "Dispositivo Cliente")


def attendance_input(
    attendance_id: str,
    *,
    customer: str = "customer-1",
    operator: str = "operator-1",
    occurred_at: datetime = NOW,
    process: ClassificationIdentity = PROCESS,
) -> AttendanceInput:
    return AttendanceInput(
        attendance_id=attendance_id,
        external_reference=f"external-{attendance_id}",
        source="local-export",
        customer_code=customer,
        operator_id=operator,
        channel="phone",
        occurred_at=occurred_at,
        process=process,
        opening_classification=OPENING,
        closing_classification=CLOSING,
    )


class FakeAttendanceRepository:
    def __init__(self) -> None:
        self.items: dict[str, AttendanceFact] = {}
        self.search_arguments: dict[str, object] = {}

    def add(self, attendance: AttendanceFact) -> None:
        self.items[attendance.id] = attendance

    def get_by_id(self, attendance_id: str) -> AttendanceFact | None:
        return self.items.get(attendance_id)

    def get_by_source_reference(
        self, *, source: str, external_reference: str
    ) -> AttendanceFact | None:
        return next(
            (
                item
                for item in self.items.values()
                if item.source == source
                and item.external_reference == external_reference
            ),
            None,
        )

    def search(self, **filters: object) -> tuple[AttendanceFact, ...]:
        self.search_arguments = filters
        return tuple(
            sorted(self.items.values(), key=lambda item: (item.occurred_at, item.id))
        )


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.attendances = FakeAttendanceRepository()
        self.commit_calls = 0
        self.rollback_calls = 0
        self.closed = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        if exc_type is not None:
            self.rollback_calls += 1
        self.closed = True

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


def test_import_is_idempotent_and_conflicting_facts_roll_back() -> None:
    unit_of_work = FakeUnitOfWork()
    service = ImportAttendancesUseCase(lambda: unit_of_work, lambda: NOW)
    command = ImportAttendancesCommand((attendance_input("attendance-1"),))

    first = service.execute(command)
    second = service.execute(command)

    assert first.created_count == 1
    assert second.created_count == 0
    assert second.already_existing_count == 1
    assert unit_of_work.commit_calls == 2
    with pytest.raises(AttendanceFactConflict):
        service.execute(
            ImportAttendancesCommand(
                (attendance_input("attendance-1", customer="other-customer"),)
            )
        )
    assert unit_of_work.rollback_calls == 1
    assert unit_of_work.closed


def test_fact_query_passes_filters_and_does_not_commit() -> None:
    unit_of_work = FakeUnitOfWork()
    service = ImportAttendancesUseCase(lambda: unit_of_work, lambda: NOW)
    service.execute(ImportAttendancesCommand((attendance_input("attendance-1"),)))
    unit_of_work.commit_calls = 0
    query = AttendanceFilters(operator_id="operator-1", channel="phone")

    result = GetAttendancesUseCase(lambda: unit_of_work).execute(query)

    assert result.items[0].attendance_id == "attendance-1"
    assert unit_of_work.attendances.search_arguments["operator_id"] == "operator-1"
    assert unit_of_work.commit_calls == 0
    assert unit_of_work.closed


def test_monthly_summary_uses_eligible_originals_and_original_operator() -> None:
    unit_of_work = FakeUnitOfWork()
    importer = ImportAttendancesUseCase(lambda: unit_of_work, lambda: NOW)
    importer.execute(
        ImportAttendancesCommand(
            (
                attendance_input(
                    "original",
                    operator="operator-original",
                    occurred_at=datetime(2026, 7, 31, 23, tzinfo=UTC),
                ),
                attendance_input(
                    "return",
                    operator="operator-return",
                    occurred_at=datetime(2026, 8, 1, 1, tzinfo=UTC),
                ),
                attendance_input(
                    "general",
                    occurred_at=datetime(2026, 7, 10, tzinfo=UTC),
                    process=ClassificationIdentity("02", "Outro processo"),
                ),
            )
        )
    )
    unit_of_work.commit_calls = 0
    query = RecurrenceCohortQuery(
        reference_month=date(2026, 7, 1),
        observed_through=date(2026, 8, 30),
    )

    result = GetRecurrenceSummaryUseCase(lambda: unit_of_work).execute(query)

    assert result.eligible_attendance_count == 1
    assert result.recurrence_count == 1
    assert result.recurrence_rate == 1
    assert result.by_operator[0].operator_id == "operator-original"
    assert result.occurrences[0].original_attendance_id == "original"
    assert unit_of_work.commit_calls == 0
    assert unit_of_work.closed


def test_cohort_requires_complete_observation_window() -> None:
    with pytest.raises(ValueError, match="observation window"):
        RecurrenceCohortQuery(
            reference_month=date(2026, 7, 1),
            observed_through=date(2026, 8, 29),
        )
