import argparse
import os
import sys
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import TextIO

from supervisor_ai.bootstrap import build_csv_import_service
from supervisor_ai.cli.formatting import (
    format_json_report,
    format_text_report,
    has_failures,
)
from supervisor_ai.infrastructure.importing import (
    CsvBatchImportResult,
    CsvImportService,
    CsvStructureError,
)

DATABASE_URL_ENV = "SUPERVISOR_AI_DATABASE_URL"


class CliExitCode(IntEnum):
    SUCCESS = 0
    PARTIAL_FAILURE = 1
    USAGE_ERROR = 2
    FILE_ERROR = 3
    CSV_STRUCTURE_ERROR = 4
    CONFIGURATION_ERROR = 5
    UNEXPECTED_ERROR = 6


@dataclass(frozen=True, slots=True)
class CsvImportCommand:
    file_path: Path
    database_url: str
    output_format: str
    verbose: bool
    debug: bool


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="supervisor-ai")
    subparsers = parser.add_subparsers(dest="command", required=True)
    import_csv = subparsers.add_parser(
        "import-csv", description="Importa eventos comerciais de um arquivo CSV."
    )
    import_csv.add_argument("file", type=Path, help="arquivo CSV em UTF-8")
    import_csv.add_argument("--database-url")
    import_csv.add_argument(
        "--output-format",
        choices=("text", "json"),
        default="text",
    )
    import_csv.add_argument("--verbose", action="store_true")
    import_csv.add_argument("--debug", action="store_true")
    return parser


def parse_command(
    argv: Sequence[str], environment: Mapping[str, str]
) -> CsvImportCommand:
    arguments = create_parser().parse_args(argv)
    database_url = resolve_database_url(arguments.database_url, environment)
    return CsvImportCommand(
        file_path=arguments.file,
        database_url=database_url,
        output_format=arguments.output_format,
        verbose=arguments.verbose,
        debug=arguments.debug,
    )


def resolve_database_url(
    argument: str | None, environment: Mapping[str, str]
) -> str:
    if argument is not None:
        if argument:
            return argument
        raise ValueError("--database-url must not be empty")
    configured = environment.get(DATABASE_URL_ENV)
    if configured:
        return configured
    raise ValueError(
        f"database URL is required via --database-url or {DATABASE_URL_ENV}"
    )


def read_csv_file(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    if not file_path.is_file():
        raise IsADirectoryError(file_path)
    return file_path.read_text(encoding="utf-8-sig")


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    environment: Mapping[str, str] | None = None,
    service_builder: Callable[[str], CsvImportService] = build_csv_import_service,
) -> int:
    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    env = os.environ if environment is None else environment
    try:
        command = parse_command(arguments, env)
    except ValueError as error:
        print(f"Configuration error: {error}", file=errors)
        return CliExitCode.CONFIGURATION_ERROR

    try:
        content = read_csv_file(command.file_path)
    except (FileNotFoundError, IsADirectoryError, PermissionError) as error:
        print(f"File error: {_file_error_message(error)}", file=errors)
        return CliExitCode.FILE_ERROR
    except UnicodeDecodeError:
        print("File error: CSV file is not valid UTF-8", file=errors)
        return CliExitCode.FILE_ERROR
    except OSError as error:
        print(f"File error: {type(error).__name__}", file=errors)
        return CliExitCode.FILE_ERROR

    try:
        service = service_builder(command.database_url)
    except Exception as error:
        print(f"Initialization error: {type(error).__name__}", file=errors)
        if command.debug:
            traceback.print_exc(file=errors)
        return CliExitCode.CONFIGURATION_ERROR

    try:
        result = service.import_csv(content)
    except CsvStructureError as error:
        print(f"CSV structure error: {error}", file=errors)
        return CliExitCode.CSV_STRUCTURE_ERROR
    except Exception as error:
        print(f"Unexpected error: {type(error).__name__}", file=errors)
        if command.debug:
            traceback.print_exc(file=errors)
        return CliExitCode.UNEXPECTED_ERROR

    _write_report(output, command, result)
    return (
        CliExitCode.PARTIAL_FAILURE
        if has_failures(result)
        else CliExitCode.SUCCESS
    )


def _write_report(
    output: TextIO, command: CsvImportCommand, result: CsvBatchImportResult
) -> None:
    if command.output_format == "json":
        output.write(format_json_report(command.file_path, result))
    else:
        output.write(
            format_text_report(
                command.file_path,
                result,
                verbose=command.verbose,
            )
        )


def _file_error_message(error: OSError) -> str:
    if isinstance(error, FileNotFoundError):
        return "CSV file does not exist"
    if isinstance(error, IsADirectoryError):
        return "CSV path is not a regular file"
    return "permission denied while reading CSV file"


if __name__ == "__main__":
    raise SystemExit(main())
