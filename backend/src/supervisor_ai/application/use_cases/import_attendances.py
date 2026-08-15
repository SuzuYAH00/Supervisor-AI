from dataclasses import dataclass
from datetime import datetime

from supervisor_ai.application.errors import AttendanceFactConflict
from supervisor_ai.application.persistence import AttendanceFact
from supervisor_ai.application.ports import Clock, UnitOfWork, UnitOfWorkFactory
from supervisor_ai.rules_engine import ClassificationIdentity


@dataclass(frozen=True, slots=True)
class AttendanceInput:
    attendance_id: str
    external_reference: str
    source: str
    customer_code: str
    operator_id: str
    channel: str
    occurred_at: datetime
    process: ClassificationIdentity
    opening_classification: ClassificationIdentity
    closing_classification: ClassificationIdentity

    def to_fact(self, created_at: datetime) -> AttendanceFact:
        return AttendanceFact(
            id=self.attendance_id,
            external_reference=self.external_reference,
            source=self.source,
            customer_code=self.customer_code,
            operator_id=self.operator_id,
            channel=self.channel,
            occurred_at=self.occurred_at,
            process=self.process,
            opening_classification=self.opening_classification,
            closing_classification=self.closing_classification,
            created_at=created_at,
        )


@dataclass(frozen=True, slots=True)
class ImportAttendancesCommand:
    attendances: tuple[AttendanceInput, ...]


@dataclass(frozen=True, slots=True)
class ImportAttendancesResult:
    received_count: int
    created_count: int
    already_existing_count: int
    attendance_ids: tuple[str, ...]


class ImportAttendancesUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(self, command: ImportAttendancesCommand) -> ImportAttendancesResult:
        created_at = self._clock()
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("clock must return timezone-aware datetimes")
        facts = tuple(item.to_fact(created_at) for item in command.attendances)
        created_count = 0
        with self._unit_of_work_factory() as unit_of_work:
            for fact in facts:
                if self._ensure_attendance(unit_of_work, fact):
                    created_count += 1
            unit_of_work.commit()
        return ImportAttendancesResult(
            received_count=len(facts),
            created_count=created_count,
            already_existing_count=len(facts) - created_count,
            attendance_ids=tuple(item.id for item in facts),
        )

    @staticmethod
    def _ensure_attendance(unit_of_work: UnitOfWork, fact: AttendanceFact) -> bool:
        by_reference = unit_of_work.attendances.get_by_source_reference(
            source=fact.source, external_reference=fact.external_reference
        )
        by_id = unit_of_work.attendances.get_by_id(fact.id)
        existing = by_reference or by_id
        if existing is None:
            unit_of_work.attendances.add(fact)
            return True
        if not _same_fact(existing, fact):
            raise AttendanceFactConflict(
                "attendance identity differs from persisted facts"
            )
        return False


def _same_fact(first: AttendanceFact, second: AttendanceFact) -> bool:
    return all(
        (
            first.id == second.id,
            first.external_reference == second.external_reference,
            first.source == second.source,
            first.customer_code == second.customer_code,
            first.operator_id == second.operator_id,
            first.channel == second.channel,
            first.occurred_at == second.occurred_at,
            first.process == second.process,
            first.opening_classification == second.opening_classification,
            first.closing_classification == second.closing_classification,
        )
    )
