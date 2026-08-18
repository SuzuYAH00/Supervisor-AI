import csv
import io
from datetime import datetime
from typing import Protocol

from supervisor_ai.application.use_cases.import_attendances import (
    AttendanceCoverageDeclaration,
    AttendanceInput,
    ImportAttendancesCommand,
    ImportAttendancesResult,
)
from supervisor_ai.rules_engine import ClassificationIdentity

ATTENDANCE_CSV_COLUMNS = (
    "attendance_id",
    "external_reference",
    "source",
    "customer_code",
    "operator_id",
    "channel",
    "occurred_at",
    "process_code",
    "process_description",
    "opening_code",
    "opening_description",
    "closing_code",
    "closing_description",
)


class AttendanceCsvStructureError(ValueError):
    """O CSV não possui o contrato estrutural de atendimentos."""


class AttendanceCsvValidationError(ValueError):
    """Uma linha não representa um fato de atendimento válido."""


class AttendanceImporter(Protocol):
    def execute(self, command: ImportAttendancesCommand) -> ImportAttendancesResult: ...


class AttendanceCsvImportService:
    def __init__(self, importer: AttendanceImporter) -> None:
        self._importer = importer

    def import_csv(
        self,
        content: str,
        *,
        coverage: AttendanceCoverageDeclaration | None = None,
    ) -> ImportAttendancesResult:
        attendances = _parse_attendance_csv(content)
        try:
            command = ImportAttendancesCommand(attendances, coverage)
        except ValueError as error:
            raise AttendanceCsvValidationError(
                "coverage source does not match attendance facts"
            ) from error
        return self._importer.execute(command)


def _parse_attendance_csv(content: str) -> tuple[AttendanceInput, ...]:
    if not content:
        raise AttendanceCsvStructureError("CSV header is missing")
    reader = csv.DictReader(io.StringIO(content), strict=True)
    _validate_header(reader.fieldnames)
    attendances: list[AttendanceInput] = []
    seen_ids: set[str] = set()
    seen_references: set[tuple[str, str]] = set()
    try:
        for row in reader:
            if None in row:
                raise AttendanceCsvValidationError(
                    f"line {reader.line_num} has extra columns"
                )
            attendance = _parse_row(row, reader.line_num)
            source_reference = (
                attendance.source,
                attendance.external_reference,
            )
            if attendance.attendance_id in seen_ids:
                raise AttendanceCsvValidationError(
                    f"line {reader.line_num} repeats attendance_id"
                )
            if source_reference in seen_references:
                raise AttendanceCsvValidationError(
                    f"line {reader.line_num} repeats source reference"
                )
            seen_ids.add(attendance.attendance_id)
            seen_references.add(source_reference)
            attendances.append(attendance)
    except csv.Error as error:
        raise AttendanceCsvStructureError("CSV structure is invalid") from error
    return tuple(attendances)


def _validate_header(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise AttendanceCsvStructureError("CSV header is missing")
    if len(fieldnames) != len(set(fieldnames)):
        raise AttendanceCsvStructureError("CSV header contains duplicate columns")
    if set(fieldnames) != set(ATTENDANCE_CSV_COLUMNS):
        raise AttendanceCsvStructureError(
            "CSV header does not match attendance contract"
        )


def _parse_row(
    row: dict[str | None, str | None], line_number: int
) -> AttendanceInput:
    occurred_at_text = _required(row, "occurred_at", line_number, 64)
    try:
        occurred_at = datetime.fromisoformat(
            occurred_at_text.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise AttendanceCsvValidationError(
            f"line {line_number} has invalid occurred_at"
        ) from error
    if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        raise AttendanceCsvValidationError(
            f"line {line_number} occurred_at must include timezone"
        )
    try:
        return AttendanceInput(
            attendance_id=_required(row, "attendance_id", line_number, 128),
            external_reference=_required(
                row, "external_reference", line_number, 255
            ),
            source=_required(row, "source", line_number, 100),
            customer_code=_required(row, "customer_code", line_number, 128),
            operator_id=_required(row, "operator_id", line_number, 128),
            channel=_required(row, "channel", line_number, 100),
            occurred_at=occurred_at,
            process=_classification(row, "process", line_number),
            opening_classification=_classification(row, "opening", line_number),
            closing_classification=_classification(row, "closing", line_number),
        )
    except ValueError as error:
        raise AttendanceCsvValidationError(
            f"line {line_number} contains invalid values"
        ) from error


def _classification(
    row: dict[str | None, str | None], prefix: str, line_number: int
) -> ClassificationIdentity:
    code_value = row.get(f"{prefix}_code")
    if code_value is None:
        raise AttendanceCsvValidationError(
            f"line {line_number} is missing {prefix}_code"
        )
    code = None if code_value == "" else code_value
    if code is not None:
        _validate_text(code, f"{prefix}_code", line_number, 20)
    description = _required(
        row, f"{prefix}_description", line_number, 255
    )
    return ClassificationIdentity(code, description)


def _required(
    row: dict[str | None, str | None],
    field: str,
    line_number: int,
    maximum_length: int,
) -> str:
    value = row.get(field)
    if value is None:
        raise AttendanceCsvValidationError(f"line {line_number} is missing {field}")
    _validate_text(value, field, line_number, maximum_length)
    return value


def _validate_text(
    value: str, field: str, line_number: int, maximum_length: int
) -> None:
    if not value.strip() or value != value.strip() or len(value) > maximum_length:
        raise AttendanceCsvValidationError(f"line {line_number} has invalid {field}")
