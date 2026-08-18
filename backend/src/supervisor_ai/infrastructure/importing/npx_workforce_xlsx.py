import hashlib
from datetime import datetime
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile
from zoneinfo import ZoneInfo

from supervisor_ai.application.use_cases.npx_delays import PauseInput, WorkSessionInput

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_TIMEZONE = ZoneInfo("America/Fortaleza")
_POINT_HEADERS = (
    "Agente ID",
    "Agente",
    "Ramal",
    "Fila",
    "Data de entrada",
    "Hora de entrada",
    "Data de saída",
    "Hora de saída",
    "Permanência",
    "Total",
)
_PAUSE_HEADERS = (
    "Agente ID",
    "Agente",
    "Ramal",
    "Fila",
    "Pausa",
    "Data de entrada",
    "Hora de entrada",
    "Data de saída",
    "Hora de saída",
    "Permanência",
    "Liberado pelo Supervisor",
    "Total",
)


class NpxWorkbookStructureError(ValueError):
    pass


def parse_npx_work_sessions_xlsx(
    content: bytes, *, extract_reference: str
) -> tuple[WorkSessionInput, ...]:
    rows = _rows(content)
    _headers(rows, _POINT_HEADERS)
    result = []
    for row_number, values in rows[2:]:
        if (
            not values
            or values[0] == "Total"
            or not any(values)
            or len(values) < 9
            or not values[1]
            or not values[4]
        ):
            continue
        started = _timestamp(values[4], values[5])
        ended = _timestamp(values[6], values[7])
        duration = _duration(values[8])
        reference = _reference("session", values[1], started, ended, values[3])
        result.append(
            WorkSessionInput(
                f"work-session-{reference}",
                f"npx-session-{reference}",
                values[1],
                values[0] or None,
                values[3],
                started,
                ended,
                duration,
                extract_reference,
                "Sheet1",
                row_number,
            )
        )
    return tuple(result)


def parse_npx_pauses_xlsx(
    content: bytes, *, extract_reference: str
) -> tuple[PauseInput, ...]:
    rows = _rows(content)
    _headers(rows, _PAUSE_HEADERS)
    result = []
    for row_number, values in rows[2:]:
        if (
            not values
            or values[0] == "Total"
            or not any(values)
            or len(values) < 11
            or not values[1]
            or not values[5]
        ):
            continue
        started = _timestamp(values[5], values[6])
        ended = _timestamp(values[7], values[8])
        duration = _duration(values[9])
        reference = _reference("pause", values[1], started, ended, values[3], values[4])
        result.append(
            PauseInput(
                f"pause-{reference}",
                f"npx-pause-{reference}",
                values[1],
                values[0] or None,
                values[3],
                started,
                ended,
                duration,
                extract_reference,
                "Sheet1",
                row_number,
                values[4],
                values[10] or None,
            )
        )
    return tuple(result)


def _headers(
    rows: tuple[tuple[int, tuple[str, ...]], ...], expected: tuple[str, ...]
) -> None:
    if len(rows) < 2 or rows[1][1] != expected:
        raise NpxWorkbookStructureError(
            "XLSX headers do not match the audited NPX export"
        )


def _rows(content: bytes) -> tuple[tuple[int, tuple[str, ...]], ...]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    except (BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise NpxWorkbookStructureError("invalid XLSX structure") from error
    result = []
    for row in root.findall(f".//{_NS}row"):
        cells: dict[int, str] = {}
        for cell in row.findall(f"{_NS}c"):
            reference = cell.attrib.get("r", "A1")
            column = _column_number(reference)
            text = "".join(item.text or "" for item in cell.iter(f"{_NS}t"))
            if not text:
                value = cell.find(f"{_NS}v")
                text = "" if value is None else value.text or ""
            cells[column] = text
        maximum = max(cells, default=0)
        result.append(
            (
                int(row.attrib["r"]),
                tuple(cells.get(index, "") for index in range(1, maximum + 1)),
            )
        )
    return tuple(result)


def _column_number(reference: str) -> int:
    letters = "".join(char for char in reference if char.isalpha())
    result = 0
    for char in letters:
        result = result * 26 + ord(char.upper()) - 64
    return result


def _timestamp(day: str, clock: str) -> datetime:
    return datetime.strptime(f"{day} {clock}", "%d/%m/%Y %H:%M:%S").replace(
        tzinfo=_TIMEZONE
    )


def _duration(value: str) -> int:
    hours, minutes, seconds = (int(item) for item in value.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def _reference(*parts: object) -> str:
    material = "\0".join(
        part.isoformat() if isinstance(part, datetime) else str(part) for part in parts
    )
    return hashlib.sha256(material.encode()).hexdigest()
