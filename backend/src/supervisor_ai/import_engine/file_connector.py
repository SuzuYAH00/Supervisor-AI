import csv
import errno
import json
import math
import stat
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeGuard

from supervisor_ai.import_engine.types import (
    RawRecord,
    RawValue,
    ReadResult,
    SourceMetadata,
    SourceReadError,
)

type RecordReader = Callable[[Path], list[RawRecord]]

_RETRYABLE_IO_ERRNOS = {
    errno.EAGAIN,
    errno.EBUSY,
    errno.EINTR,
    errno.ETIMEDOUT,
}


class FileConnector:
    """Lê registros brutos de um arquivo local CSV ou JSON.

    CSV vazio, contendo somente o cabeçalho ou somente linhas em branco é uma
    leitura válida sem registros.
    """

    _readers: dict[str, RecordReader]

    def __init__(self, path: str | Path, source_name: str) -> None:
        self.path = Path(path)
        self.source_name = source_name
        self._readers = {
            ".csv": self._read_csv,
            ".json": self._read_json,
        }

    def read(self) -> ReadResult:
        """Lê o arquivo e converte falhas técnicas em ``SourceReadError``."""
        try:
            file_stat = self.path.stat()
        except OSError as error:
            raise self._access_error(error) from error

        if stat.S_ISDIR(file_stat.st_mode):
            raise SourceReadError(
                self.source_name,
                "Source path is a directory, not a file.",
            )
        if not stat.S_ISREG(file_stat.st_mode):
            raise SourceReadError(
                self.source_name,
                "Source path is not a regular file.",
            )

        extension = self.path.suffix.lower()
        reader = self._readers.get(extension)
        if reader is None:
            raise SourceReadError(
                self.source_name,
                "Source file extension is not supported.",
            )

        try:
            records = reader(self.path)
        except _InvalidFileError as error:
            raise SourceReadError(self.source_name, str(error)) from error
        except OSError as error:
            raise self._access_error(error) from error

        return ReadResult(
            records=records,
            metadata=SourceMetadata(
                source_name=self.source_name,
                read_at=datetime.now(UTC),
                attributes={
                    "file_name": self.path.name,
                    "file_extension": extension,
                    "format": extension.removeprefix("."),
                    "size_bytes": file_stat.st_size,
                },
            ),
        )

    def _access_error(self, error: OSError) -> SourceReadError:
        if isinstance(error, FileNotFoundError):
            message = "Source file does not exist."
            retryable = False
        elif isinstance(error, PermissionError):
            message = "Permission denied while reading source file."
            retryable = False
        else:
            message = "Source file could not be read due to an I/O error."
            retryable = error.errno in _RETRYABLE_IO_ERRNOS

        return SourceReadError(
            self.source_name,
            message,
            retryable=retryable,
        )

    @staticmethod
    def _read_csv(path: Path) -> list[RawRecord]:
        records: list[RawRecord] = []

        try:
            with path.open(encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file, strict=True)
                fieldnames = reader.fieldnames
                if fieldnames is not None and (
                    any(not fieldname.strip() for fieldname in fieldnames)
                    or len(fieldnames) != len(set(fieldnames))
                ):
                    raise _InvalidFileError("Source CSV headers are invalid.")

                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise _InvalidFileError("Source CSV file is invalid.")

                    records.append(
                        RawRecord(
                            data=dict(row),
                            metadata={
                                "file_name": path.name,
                                "line_number": reader.line_num,
                            },
                        )
                    )
        except (csv.Error, UnicodeError) as error:
            raise _InvalidFileError("Source CSV file is invalid.") from error

        return records

    @staticmethod
    def _read_json(path: Path) -> list[RawRecord]:
        try:
            with path.open(encoding="utf-8") as file:
                payload: object = json.load(
                    file,
                    object_pairs_hook=_reject_duplicate_keys,
                    parse_constant=_reject_constant,
                )
        except (json.JSONDecodeError, UnicodeError, ValueError) as error:
            raise _InvalidFileError("Source JSON file is invalid.") from error

        if not isinstance(payload, list):
            raise _InvalidFileError(
                "Source JSON root must be a list of objects."
            )

        records: list[RawRecord] = []
        for index, item in enumerate(payload):
            if not isinstance(item, dict) or not _is_raw_value(item):
                raise _InvalidFileError(
                    "Source JSON items must be objects with JSON-compatible values."
                )

            records.append(
                RawRecord(
                    data=item,
                    metadata={"file_name": path.name, "record_index": index},
                )
            )

        return records


class _InvalidFileError(Exception):
    """Erro interno usado para sanitizar falhas de formato."""


def _reject_constant(_value: str) -> None:
    raise ValueError


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidFileError("Source JSON file contains duplicate keys.")
        result[key] = value
    return result


def _is_raw_value(value: object) -> TypeGuard[RawValue]:
    if value is None or isinstance(value, str | bool | int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_raw_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_raw_value(item)
            for key, item in value.items()
        )
    return False
