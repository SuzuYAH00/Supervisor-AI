from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import PurePosixPath
from typing import Protocol
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from supervisor_ai.application.use_cases.import_csat_contacts import (
    CsatContactInput,
    ImportCsatContactsCommand,
    ImportCsatContactsResult,
)
from supervisor_ai.rules_engine import CsatCompetitiveChannel

MK_CSAT_SOURCE = "mk"
NPX_CSAT_SOURCE = "npx"
_MK_HEADERS = (
    "Nota",
    "Data",
    "Tempo Total",
    "Setor",
    "Operador final",
    "Canal",
    "Cliente",
    "Atendimento humano",
    "Em fila",
    "Protocolo",
    "N° de contato",
)
_NPX_HEADERS = (
    "Código",
    "Agente",
    "Data",
    "Telefone",
    "Tempo total",
    "Tempo espera",
    "Linkedid",
    "P1",
    "P2",
    "P3",
    "Gravação",
)
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PACKAGE_REL_NS = (
    "{http://schemas.openxmlformats.org/package/2006/relationships}"
)


class CsatSourceXlsxStructureError(ValueError):
    """O XLSX não possui um dos contratos estruturais auditados de CSAT."""


class CsatSourceXlsxValidationError(ValueError):
    """Uma linha do XLSX não representa um contato CSAT válido."""


class CsatContactImporter(Protocol):
    def execute(
        self, command: ImportCsatContactsCommand
    ) -> ImportCsatContactsResult: ...


class MkCsatXlsxImportService:
    def __init__(self, importer: CsatContactImporter) -> None:
        self._importer = importer

    def import_xlsx(self, content: bytes) -> ImportCsatContactsResult:
        return self._importer.execute(
            ImportCsatContactsCommand(parse_mk_csat_xlsx(content))
        )


class NpxCsatXlsxImportService:
    def __init__(self, importer: CsatContactImporter) -> None:
        self._importer = importer

    def import_xlsx(self, content: bytes) -> ImportCsatContactsResult:
        return self._importer.execute(
            ImportCsatContactsCommand(parse_npx_csat_xlsx(content))
        )


def parse_mk_csat_xlsx(content: bytes) -> tuple[CsatContactInput, ...]:
    rows = _read_rows(content)
    header_index = _require_header(rows, _MK_HEADERS, 1)
    contacts: list[CsatContactInput] = []
    references: set[str] = set()
    for row in rows[header_index + 1 :]:
        values = _row_values(row, len(_MK_HEADERS))
        if not any(values):
            continue
        line = row.number
        score_text, date_text, _, sector, operator, _, _, _, _, protocol, _ = values
        _required(operator, "Operador final", line)
        if operator.strip() == "MKBOT assistant":
            continue
        _required(protocol, "Protocolo", line)
        _required(sector, "Setor", line)
        if protocol in references:
            raise CsatSourceXlsxValidationError(
                f"row {line} repeats Protocolo"
            )
        references.add(protocol)
        score = _mk_score(score_text, line)
        occurred_on = _date_value(date_text, "%d/%m/%Y %H:%M:%S", line)
        contacts.append(
            CsatContactInput(
                external_reference=protocol,
                source=MK_CSAT_SOURCE,
                external_operator_identity=operator,
                occurred_on=occurred_on,
                source_channel=CsatCompetitiveChannel.CHAT,
                score=score,
                source_context=sector,
            )
        )
    return tuple(contacts)


def parse_npx_csat_xlsx(content: bytes) -> tuple[CsatContactInput, ...]:
    rows = _read_rows(content)
    header_index = _require_header(rows, _NPX_HEADERS, 2)
    contacts: list[CsatContactInput] = []
    references: set[str] = set()
    for row in rows[header_index + 1 :]:
        values = _row_values(row, len(_NPX_HEADERS))
        if not any(values):
            continue
        line = row.number
        _, agent, date_text, _, _, _, linked_id, p1, p2, p3, _ = values
        _required(agent, "Agente", line)
        _required(linked_id, "Linkedid", line)
        if linked_id in references:
            raise CsatSourceXlsxValidationError(
                f"row {line} repeats Linkedid"
            )
        references.add(linked_id)
        score = _npx_score(p1, p2, p3, line)
        contacts.append(
            CsatContactInput(
                external_reference=linked_id,
                source=NPX_CSAT_SOURCE,
                external_operator_identity=agent,
                occurred_on=_date_value(date_text, "%d/%m/%Y", line),
                source_channel=CsatCompetitiveChannel.PHONE,
                score=score,
            )
        )
    return tuple(contacts)


@dataclass(frozen=True, slots=True)
class _Row:
    number: int
    cells: dict[int, str]


def _read_rows(content: bytes) -> tuple[_Row, ...]:
    if not content:
        raise CsatSourceXlsxStructureError("XLSX file is empty")
    try:
        with ZipFile(BytesIO(content)) as archive:
            shared_strings = _shared_strings(archive)
            sheet_path = _first_sheet_path(archive)
            root = ElementTree.fromstring(archive.read(sheet_path))
            return tuple(
                _Row(
                    number=int(row.attrib["r"]),
                    cells={
                        _column_number(cell.attrib["r"]): _cell_value(
                            cell, shared_strings
                        )
                        for cell in row.findall(f"{_NS}c")
                    },
                )
                for row in root.findall(f".//{_NS}sheetData/{_NS}row")
            )
    except (
        BadZipFile,
        IndexError,
        KeyError,
        ElementTree.ParseError,
        ValueError,
    ) as error:
        raise CsatSourceXlsxStructureError("XLSX structure is invalid") from error


def _first_sheet_path(archive: ZipFile) -> str:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(
        archive.read("xl/_rels/workbook.xml.rels")
    )
    sheet = workbook.find(f"{_NS}sheets/{_NS}sheet")
    if sheet is None:
        raise CsatSourceXlsxStructureError("XLSX has no worksheet")
    targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall(f"{_PACKAGE_REL_NS}Relationship")
    }
    target = targets[sheet.attrib[f"{_REL_NS}id"]].lstrip("/")
    return target if target.startswith("xl/") else str(PurePosixPath("xl") / target)


def _shared_strings(archive: ZipFile) -> tuple[str, ...]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return ()
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return tuple(
        "".join(text.text or "" for text in item.iter(f"{_NS}t"))
        for item in root.findall(f"{_NS}si")
    )


def _cell_value(cell: ElementTree.Element, shared: tuple[str, ...]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(text.text or "" for text in cell.iter(f"{_NS}t"))
    value = cell.findtext(f"{_NS}v")
    if value is None:
        return ""
    if cell.attrib.get("t") == "s":
        return shared[int(value)]
    return value


def _column_number(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    if not letters:
        raise ValueError("cell reference has no column")
    result = 0
    for character in letters:
        result = result * 26 + ord(character) - ord("A") + 1
    return result


def _row_values(row: _Row, length: int) -> tuple[str, ...]:
    if any(column > length for column, value in row.cells.items() if value):
        raise CsatSourceXlsxStructureError(
            f"row {row.number} has values outside the expected schema"
        )
    return tuple(row.cells.get(column, "") for column in range(1, length + 1))


def _require_header(
    rows: tuple[_Row, ...], expected: tuple[str, ...], row_number: int
) -> int:
    for index, row in enumerate(rows):
        if row.number == row_number:
            if _row_values(row, len(expected)) != expected:
                raise CsatSourceXlsxStructureError(
                    "XLSX header does not match the audited source contract"
                )
            return index
    raise CsatSourceXlsxStructureError("XLSX header is missing")


def _mk_score(value: str, line: int) -> Decimal | None:
    if value == "-1":
        return None
    return _score(value, Decimal("0"), line)


def _npx_score(p1: str, p2: str, p3: str, line: int) -> Decimal | None:
    unanswered = tuple(value.lower() == "x" for value in (p1, p2, p3))
    if all(unanswered):
        return None
    if any(unanswered) or any(not value for value in (p1, p2, p3)):
        raise CsatSourceXlsxValidationError(
            f"row {line} contains a partial NPX response"
        )
    return _score(p2, Decimal("1"), line)


def _score(value: str, minimum: Decimal, line: int) -> Decimal:
    try:
        score = Decimal(value)
    except InvalidOperation as error:
        raise CsatSourceXlsxValidationError(
            f"row {line} has an invalid CSAT score"
        ) from error
    if not score.is_finite() or score < minimum or score > Decimal("5"):
        raise CsatSourceXlsxValidationError(
            f"row {line} has an invalid CSAT score"
        )
    return score


def _date_value(value: str, pattern: str, line: int) -> date:
    try:
        return datetime.strptime(value, pattern).date()
    except ValueError as error:
        raise CsatSourceXlsxValidationError(
            f"row {line} has an invalid attendance date"
        ) from error


def _required(value: str, field: str, line: int) -> None:
    if not value.strip():
        raise CsatSourceXlsxValidationError(
            f"row {line} is missing {field}"
        )
