from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from pathlib import PurePosixPath
from typing import Protocol
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile
from zoneinfo import ZoneInfo

from supervisor_ai.application.use_cases.import_employee_occurrence_reports import (
    EmployeeOccurrenceImportIssue,
    EmployeeOccurrenceReportInput,
    ImportEmployeeOccurrenceReportsCommand,
    ImportEmployeeOccurrenceReportsResult,
)

EMPLOYEE_OCCURRENCE_SOURCE = "google_forms_employee_occurrences"
EMPLOYEE_OCCURRENCE_SHEET = "Respostas ao formulário 1"
EMPLOYEE_OCCURRENCE_HEADERS = (
    "Carimbo de data/hora",
    "Técnico de Suporte",
    "Data - (DD/MM/AA)",
    "Motivo Ocorrência",
    "Pontuação",
)
_OPERATIONAL_TIMEZONE = ZoneInfo("America/Fortaleza")
_DATE_PATTERN = re.compile(r"(\d{2})/(\d{2})/(\d{2}|\d{4})")
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class EmployeeOccurrenceXlsxStructureError(ValueError):
    """O arquivo não possui o contrato estrutural esperado do Google Forms."""


@dataclass(frozen=True, slots=True)
class ParsedEmployeeOccurrenceWorkbook:
    total_data_rows: int
    reports: tuple[EmployeeOccurrenceReportInput, ...]
    issues: tuple[EmployeeOccurrenceImportIssue, ...]


@dataclass(frozen=True, slots=True)
class EmployeeOccurrenceXlsxImportResult:
    total_data_rows: int
    imported_rows: int
    idempotent_rows: int
    rejected_rows: int
    conflict_rows: int
    issues: tuple[EmployeeOccurrenceImportIssue, ...]


class EmployeeOccurrenceReportsImporter(Protocol):
    def execute(
        self, command: ImportEmployeeOccurrenceReportsCommand
    ) -> ImportEmployeeOccurrenceReportsResult: ...


class EmployeeOccurrenceXlsxImportService:
    def __init__(self, importer: EmployeeOccurrenceReportsImporter) -> None:
        self._importer = importer

    def import_xlsx(self, content: bytes) -> EmployeeOccurrenceXlsxImportResult:
        parsed = parse_employee_occurrence_xlsx(content)
        imported = self._importer.execute(
            ImportEmployeeOccurrenceReportsCommand(parsed.reports)
        )
        all_issues = parsed.issues + imported.issues
        rejected_rows = len(parsed.issues) + sum(
            issue.code == "unknown_collaborator_alias" for issue in imported.issues
        )
        return EmployeeOccurrenceXlsxImportResult(
            total_data_rows=parsed.total_data_rows,
            imported_rows=imported.imported_rows,
            idempotent_rows=imported.idempotent_rows,
            rejected_rows=rejected_rows,
            conflict_rows=imported.conflict_rows,
            issues=all_issues,
        )


def parse_employee_occurrence_xlsx(
    content: bytes,
) -> ParsedEmployeeOccurrenceWorkbook:
    if not content:
        raise EmployeeOccurrenceXlsxStructureError("XLSX file is empty")
    try:
        with ZipFile(BytesIO(content)) as archive:
            strings = _read_shared_strings(archive)
            sheet_path = _find_sheet(archive)
            rows = _read_rows(archive, sheet_path, strings)
    except (BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise EmployeeOccurrenceXlsxStructureError(
            "XLSX structure is invalid"
        ) from error
    if not rows or tuple(rows[0][1].get(index, "") for index in range(1, 6)) != (
        EMPLOYEE_OCCURRENCE_HEADERS
    ):
        raise EmployeeOccurrenceXlsxStructureError(
            "XLSX headers do not match the employee occurrence form"
        )
    reports: list[EmployeeOccurrenceReportInput] = []
    issues: list[EmployeeOccurrenceImportIssue] = []
    total = 0
    for row_number, values in rows[1:]:
        if not any(values.get(index, "") for index in range(1, 6)):
            continue
        total += 1
        parsed = _parse_data_row(row_number, values)
        if isinstance(parsed, EmployeeOccurrenceImportIssue):
            issues.append(parsed)
        else:
            reports.append(parsed)
    return ParsedEmployeeOccurrenceWorkbook(total, tuple(reports), tuple(issues))


def _parse_data_row(
    row_number: int, values: dict[int, str]
) -> EmployeeOccurrenceReportInput | EmployeeOccurrenceImportIssue:
    submitted_raw = values.get(1, "")
    external_identity = values.get(2, "")
    occurrence_raw = values.get(3, "")
    reason_text = values.get(4, "")
    if not external_identity.strip():
        return _issue(
            row_number,
            external_identity,
            "invalid_required_field",
            external_identity,
        )
    if not reason_text.strip():
        return _issue(
            row_number, external_identity, "invalid_required_field", reason_text
        )
    try:
        submitted_at = _parse_submitted_at(submitted_raw)
    except (OverflowError, ValueError):
        return _issue(
            row_number, external_identity, "invalid_submitted_at", submitted_raw
        )
    try:
        occurrence_date = _parse_occurrence_date(occurrence_raw)
    except ValueError:
        return _issue(
            row_number,
            external_identity,
            "invalid_occurrence_date",
            occurrence_raw,
        )
    identity_material = (
        f"{EMPLOYEE_OCCURRENCE_SOURCE}\0{external_identity}\0"
        f"{submitted_at.astimezone(UTC).isoformat(timespec='microseconds')}"
    )
    digest = hashlib.sha256(identity_material.encode()).hexdigest()
    return EmployeeOccurrenceReportInput(
        report_id=f"employee-occurrence-{digest}",
        external_reference=f"google-forms-response-{digest}",
        source=EMPLOYEE_OCCURRENCE_SOURCE,
        external_identity=external_identity,
        submitted_at=submitted_at,
        occurrence_date=occurrence_date,
        reason_text=reason_text,
        source_sheet=EMPLOYEE_OCCURRENCE_SHEET,
        source_row=row_number,
    )


def _parse_submitted_at(value: str) -> datetime:
    try:
        serial = float(value)
    except ValueError as error:
        raise ValueError("submitted timestamp must be an Excel serial") from error
    if not math.isfinite(serial) or serial <= 0:
        raise ValueError("submitted timestamp must be positive")
    local = datetime(1899, 12, 30) + timedelta(days=serial)
    return local.replace(tzinfo=_OPERATIONAL_TIMEZONE)


def _parse_occurrence_date(value: str) -> date:
    match = _DATE_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("occurrence date has an invalid format")
    year_text = match.group(3)
    year = int(year_text) if len(year_text) == 4 else 2000 + int(year_text)
    return date(year, int(match.group(2)), int(match.group(1)))


def _issue(
    row_number: int,
    external_identity: str,
    code: str,
    invalid_value: str,
) -> EmployeeOccurrenceImportIssue:
    return EmployeeOccurrenceImportIssue(
        row_number, external_identity, code, invalid_value
    )


def _find_sheet(archive: ZipFile) -> str:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall(f"{_PACKAGE_REL_NS}Relationship")
    }
    for sheet in workbook.findall(f"{_NS}sheets/{_NS}sheet"):
        if sheet.attrib["name"] == EMPLOYEE_OCCURRENCE_SHEET:
            target = targets[sheet.attrib[f"{_REL_NS}id"]].lstrip("/")
            return (
                target
                if target.startswith("xl/")
                else str(PurePosixPath("xl") / target)
            )
    raise EmployeeOccurrenceXlsxStructureError(
        "XLSX does not contain the employee occurrence response sheet"
    )


def _read_shared_strings(archive: ZipFile) -> tuple[str, ...]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return ()
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return tuple(
        "".join(text.text or "" for text in item.iter(f"{_NS}t"))
        for item in root.findall(f"{_NS}si")
    )


def _read_rows(
    archive: ZipFile, path: str, strings: tuple[str, ...]
) -> tuple[tuple[int, dict[int, str]], ...]:
    root = ElementTree.fromstring(archive.read(path))
    result = []
    for row in root.findall(f".//{_NS}row"):
        values: dict[int, str] = {}
        for cell in row.findall(f"{_NS}c"):
            reference = cell.attrib["r"]
            match = re.fullmatch(r"([A-Z]+)\d+", reference)
            if match is None:
                raise EmployeeOccurrenceXlsxStructureError(
                    "XLSX contains an invalid cell reference"
                )
            index = _column_number(match.group(1))
            values[index] = _cell_value(cell, strings)
        result.append((int(row.attrib["r"]), values))
    return tuple(result)


def _column_number(letters: str) -> int:
    result = 0
    for character in letters:
        result = result * 26 + ord(character) - 64
    return result


def _cell_value(node: ElementTree.Element, strings: tuple[str, ...]) -> str:
    if node.attrib.get("t") == "inlineStr":
        return "".join(text.text or "" for text in node.iter(f"{_NS}t"))
    value = node.findtext(f"{_NS}v")
    if value is None:
        return ""
    if node.attrib.get("t") == "s":
        try:
            return strings[int(value)]
        except (IndexError, ValueError) as error:
            raise EmployeeOccurrenceXlsxStructureError(
                "XLSX contains an invalid shared string reference"
            ) from error
    return value
