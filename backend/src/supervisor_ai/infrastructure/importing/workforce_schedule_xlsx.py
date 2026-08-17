from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO
from pathlib import PurePosixPath
from typing import Protocol
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from supervisor_ai.application.use_cases.import_daily_work_statuses import (
    DailyWorkStatusInput,
    ImportDailyWorkStatusesCommand,
    ImportDailyWorkStatusesResult,
)

ATTENDANCE_SHEET_SOURCE = "attendance_sheet"
_VALID_FROM = date(2026, 4, 1)
_MAIN_SHEET = re.compile(
    r"^ESCALA - (JANEIRO|FEVEREIRO|MARÇO|ABRIL|MAIO|JUNHO|JULHO|"
    r"AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO) (\d{4})$"
)
_MONTHS = {
    "JANEIRO": 1,
    "FEVEREIRO": 2,
    "MARÇO": 3,
    "ABRIL": 4,
    "MAIO": 5,
    "JUNHO": 6,
    "JULHO": 7,
    "AGOSTO": 8,
    "SETEMBRO": 9,
    "OUTUBRO": 10,
    "NOVEMBRO": 11,
    "DEZEMBRO": 12,
}
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class WorkforceScheduleXlsxError(ValueError):
    """A planilha não possui o contrato estrutural normativo de abril/2026+."""


class DailyWorkStatusImporter(Protocol):
    def execute(
        self, command: ImportDailyWorkStatusesCommand
    ) -> ImportDailyWorkStatusesResult: ...


class WorkforceScheduleXlsxImportService:
    def __init__(self, importer: DailyWorkStatusImporter) -> None:
        self._importer = importer

    def import_xlsx(self, content: bytes) -> ImportDailyWorkStatusesResult:
        return self._importer.execute(
            ImportDailyWorkStatusesCommand(parse_workforce_schedule_xlsx(content))
        )


@dataclass(frozen=True, slots=True)
class _Sheet:
    name: str
    path: str
    competence_month: date


def parse_workforce_schedule_xlsx(
    content: bytes,
) -> tuple[DailyWorkStatusInput, ...]:
    if not content:
        raise WorkforceScheduleXlsxError("XLSX file is empty")
    try:
        with ZipFile(BytesIO(content)) as archive:
            shared_strings = _read_shared_strings(archive)
            sheets = _read_normative_sheets(archive)
            if not sheets:
                raise WorkforceScheduleXlsxError(
                    "XLSX has no schedule sheet from April 2026 onwards"
                )
            facts: list[DailyWorkStatusInput] = []
            references: set[str] = set()
            for sheet in sheets:
                parsed = _parse_sheet(archive, sheet, shared_strings)
                for fact in parsed:
                    if fact.external_reference in references:
                        raise WorkforceScheduleXlsxError(
                            "XLSX repeats a daily source reference"
                        )
                    references.add(fact.external_reference)
                    facts.append(fact)
            return tuple(facts)
    except (BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise WorkforceScheduleXlsxError("XLSX structure is invalid") from error


def _read_normative_sheets(archive: ZipFile) -> tuple[_Sheet, ...]:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(
        archive.read("xl/_rels/workbook.xml.rels")
    )
    targets = {
        relationship.attrib["Id"]: relationship.attrib["Target"]
        for relationship in relationships.findall(f"{_PACKAGE_REL_NS}Relationship")
    }
    sheets: list[_Sheet] = []
    for node in workbook.findall(f"{_NS}sheets/{_NS}sheet"):
        name = node.attrib["name"]
        match = _MAIN_SHEET.fullmatch(name)
        if match is None:
            continue
        competence = date(int(match.group(2)), _MONTHS[match.group(1)], 1)
        if competence < _VALID_FROM:
            continue
        relationship_id = node.attrib[f"{_REL_NS}id"]
        target = targets[relationship_id].lstrip("/")
        path = str(PurePosixPath("xl") / target)
        sheets.append(_Sheet(name, path, competence))
    return tuple(sheets)


def _read_shared_strings(archive: ZipFile) -> tuple[str, ...]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return ()
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return tuple(
        "".join(text.text or "" for text in item.iter(f"{_NS}t"))
        for item in root.findall(f"{_NS}si")
    )


def _parse_sheet(
    archive: ZipFile,
    sheet: _Sheet,
    shared_strings: tuple[str, ...],
) -> tuple[DailyWorkStatusInput, ...]:
    root = ElementTree.fromstring(archive.read(sheet.path))
    cells = {
        node.attrib["r"]: _cell_value(node, shared_strings)
        for node in root.findall(f".//{_NS}c")
    }
    date_columns = _date_columns(cells, sheet.competence_month)
    employee_rows = _validated_employee_rows(root)
    if not date_columns or not employee_rows:
        raise WorkforceScheduleXlsxError(
            f"sheet {sheet.name!r} lacks dates or employee validation rows"
        )
    facts: list[DailyWorkStatusInput] = []
    for row in employee_rows:
        external_identity = cells.get(f"A{row}")
        if external_identity is None or external_identity == "":
            continue
        for column, work_date in date_columns.items():
            cell = f"{column}{row}"
            raw_code = cells.get(cell)
            if raw_code is None or raw_code == "":
                continue
            if raw_code != raw_code.strip() or len(raw_code) > 20:
                raise WorkforceScheduleXlsxError(
                    f"sheet {sheet.name!r} has invalid code at {cell}"
                )
            external_reference = f"{sheet.name}!{cell}"
            digest = hashlib.sha256(
                f"{ATTENDANCE_SHEET_SOURCE}\0{external_reference}".encode()
            ).hexdigest()
            facts.append(
                DailyWorkStatusInput(
                    fact_id=f"daily-work-{digest}",
                    external_identity=external_identity,
                    work_date=work_date,
                    competence_month=sheet.competence_month,
                    raw_code=raw_code,
                    source=ATTENDANCE_SHEET_SOURCE,
                    external_reference=external_reference,
                    source_sheet=sheet.name,
                    source_cell=cell,
                )
            )
    return tuple(facts)


def _date_columns(
    cells: dict[str, str], competence_month: date
) -> dict[str, date]:
    result: dict[str, date] = {}
    for reference, value in cells.items():
        column, row = _split_reference(reference)
        if row != 1 or column == "A":
            continue
        try:
            cell_date = date(1899, 12, 30) + timedelta(days=int(float(value)))
        except ValueError:
            continue
        if (cell_date.year, cell_date.month) == (
            competence_month.year,
            competence_month.month,
        ):
            result[column] = cell_date
    return result


def _validated_employee_rows(root: ElementTree.Element) -> tuple[int, ...]:
    rows: set[int] = set()
    for validation in root.findall(f".//{_NS}dataValidation"):
        for area in validation.attrib.get("sqref", "").split():
            match = re.fullmatch(r"[A-Z]+(\d+):[A-Z]+(\d+)", area)
            if match is None:
                continue
            rows.update(range(int(match.group(1)), int(match.group(2)) + 1))
    return tuple(sorted(rows))


def _cell_value(
    node: ElementTree.Element, shared_strings: tuple[str, ...]
) -> str:
    cell_type = node.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in node.iter(f"{_NS}t"))
    value = node.findtext(f"{_NS}v")
    if value is None:
        return ""
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (IndexError, ValueError) as error:
            raise WorkforceScheduleXlsxError(
                "XLSX contains an invalid shared string reference"
            ) from error
    return value


def _split_reference(reference: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Z]+)(\d+)", reference)
    if match is None:
        raise WorkforceScheduleXlsxError("XLSX contains an invalid cell reference")
    return match.group(1), int(match.group(2))
