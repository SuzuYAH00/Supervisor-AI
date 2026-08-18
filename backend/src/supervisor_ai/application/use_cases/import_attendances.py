from dataclasses import dataclass
from datetime import date, datetime

from supervisor_ai.application.errors import (
    AttendanceFactConflict,
    IngestionCoverageConflict,
)
from supervisor_ai.application.persistence import (
    AttendanceFact,
    IngestionCoverageEvidence,
)
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
    coverage: "AttendanceCoverageDeclaration | None" = None

    def __post_init__(self) -> None:
        if self.coverage is not None and any(
            item.source != self.coverage.source for item in self.attendances
        ):
            raise ValueError(
                "all attendance facts must match the declared coverage source"
            )


@dataclass(frozen=True, slots=True)
class AttendanceCoverageDeclaration:
    source: str
    covered_through: date
    import_reference: str

    def __post_init__(self) -> None:
        for name, value, maximum in (
            ("source", self.source, 100),
            ("import_reference", self.import_reference, 255),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")


@dataclass(frozen=True, slots=True)
class ImportAttendancesResult:
    received_count: int
    created_count: int
    already_existing_count: int
    attendance_ids: tuple[str, ...]
    declared_covered_through: date | None = None
    effective_covered_through: date | None = None


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
            effective_coverage = self._record_coverage(
                unit_of_work, command.coverage, created_at
            )
            unit_of_work.commit()
        return ImportAttendancesResult(
            received_count=len(facts),
            created_count=created_count,
            already_existing_count=len(facts) - created_count,
            attendance_ids=tuple(item.id for item in facts),
            declared_covered_through=(
                command.coverage.covered_through
                if command.coverage is not None
                else None
            ),
            effective_covered_through=(
                effective_coverage.covered_through
                if effective_coverage is not None
                else None
            ),
        )

    @staticmethod
    def _record_coverage(
        unit_of_work: UnitOfWork,
        declaration: AttendanceCoverageDeclaration | None,
        recorded_at: datetime,
    ) -> IngestionCoverageEvidence | None:
        if declaration is None:
            return None
        evidence = IngestionCoverageEvidence(
            dataset=RECURRENCE_ATTENDANCES_DATASET,
            source=declaration.source,
            import_reference=declaration.import_reference,
            covered_through=declaration.covered_through,
            recorded_at=recorded_at,
        )
        existing = unit_of_work.ingestion_coverages.get_by_import_reference(
            dataset=evidence.dataset,
            source=evidence.source,
            import_reference=evidence.import_reference,
        )
        if existing is None:
            unit_of_work.ingestion_coverages.add(evidence)
        elif (
            existing.dataset != evidence.dataset
            or existing.source != evidence.source
            or existing.import_reference != evidence.import_reference
            or existing.covered_through != evidence.covered_through
        ):
            raise IngestionCoverageConflict(
                "ingestion coverage reference differs from persisted evidence"
            )
        return unit_of_work.ingestion_coverages.get_latest(
            dataset=evidence.dataset,
            source=evidence.source,
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
RECURRENCE_ATTENDANCES_DATASET = "recurrence_attendances"
