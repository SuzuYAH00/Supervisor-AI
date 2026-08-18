from dataclasses import dataclass
from datetime import date, datetime

from supervisor_ai.application.persistence import EmployeeOccurrenceReport
from supervisor_ai.application.ports import Clock, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class EmployeeOccurrenceReportInput:
    report_id: str
    external_reference: str
    source: str
    external_identity: str
    submitted_at: datetime
    occurrence_date: date
    reason_text: str
    source_sheet: str
    source_row: int


@dataclass(frozen=True, slots=True)
class EmployeeOccurrenceImportIssue:
    row_number: int
    external_identity: str
    code: str
    invalid_value: str | None


@dataclass(frozen=True, slots=True)
class ImportEmployeeOccurrenceReportsCommand:
    reports: tuple[EmployeeOccurrenceReportInput, ...]


@dataclass(frozen=True, slots=True)
class ImportEmployeeOccurrenceReportsResult:
    imported_rows: int
    idempotent_rows: int
    conflict_rows: int
    issues: tuple[EmployeeOccurrenceImportIssue, ...]


class ImportEmployeeOccurrenceReportsUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(
        self, command: ImportEmployeeOccurrenceReportsCommand
    ) -> ImportEmployeeOccurrenceReportsResult:
        created_at = self._clock()
        _require_aware(created_at)
        imported = 0
        idempotent = 0
        conflicts = 0
        issues: list[EmployeeOccurrenceImportIssue] = []
        with self._unit_of_work_factory() as unit_of_work:
            for item in command.reports:
                identity = (
                    unit_of_work.collaborator_external_identities
                    .get_by_source_identity(
                        source=item.source,
                        external_identity=item.external_identity,
                    )
                )
                if identity is None:
                    issues.append(
                        EmployeeOccurrenceImportIssue(
                            item.source_row,
                            item.external_identity,
                            "unknown_collaborator_alias",
                            item.external_identity,
                        )
                    )
                    continue
                report = _to_report(item, identity.collaborator_id, created_at)
                existing = (
                    unit_of_work.employee_occurrence_reports.get_by_source_reference(
                        source=report.source,
                        external_reference=report.external_reference,
                    )
                    or unit_of_work.employee_occurrence_reports.get_by_id(report.id)
                )
                if existing is None:
                    unit_of_work.employee_occurrence_reports.add(report)
                    imported += 1
                elif _same_facts(existing, report):
                    idempotent += 1
                else:
                    conflicts += 1
                    issues.append(
                        EmployeeOccurrenceImportIssue(
                            item.source_row,
                            item.external_identity,
                            "conflicting_occurrence",
                            item.external_reference,
                        )
                    )
            unit_of_work.commit()
        return ImportEmployeeOccurrenceReportsResult(
            imported,
            idempotent,
            conflicts,
            tuple(issues),
        )


def _to_report(
    item: EmployeeOccurrenceReportInput,
    collaborator_id: str,
    created_at: datetime,
) -> EmployeeOccurrenceReport:
    return EmployeeOccurrenceReport(
        id=item.report_id,
        external_reference=item.external_reference,
        source=item.source,
        collaborator_id=collaborator_id,
        external_collaborator_identity=item.external_identity,
        submitted_at=item.submitted_at,
        occurrence_date=item.occurrence_date,
        reason_text=item.reason_text,
        source_sheet=item.source_sheet,
        source_row=item.source_row,
        created_at=created_at,
    )


def _same_facts(
    first: EmployeeOccurrenceReport, second: EmployeeOccurrenceReport
) -> bool:
    return all(
        (
            first.id == second.id,
            first.external_reference == second.external_reference,
            first.source == second.source,
            first.collaborator_id == second.collaborator_id,
            first.external_collaborator_identity
            == second.external_collaborator_identity,
            first.submitted_at == second.submitted_at,
            first.occurrence_date == second.occurrence_date,
            first.reason_text == second.reason_text,
        )
    )


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return timezone-aware datetimes")
