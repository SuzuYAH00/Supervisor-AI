from datetime import date, timedelta

import pytest

from supervisor_ai.application.use_cases import (
    AttendanceCoverageDeclaration,
    ImportAttendancesCommand,
    ImportAttendancesResult,
)
from supervisor_ai.infrastructure.importing import (
    ATTENDANCE_CSV_COLUMNS,
    AttendanceCsvImportService,
    AttendanceCsvStructureError,
    AttendanceCsvValidationError,
)

HEADER = ",".join(ATTENDANCE_CSV_COLUMNS) + "\n"


class CapturingImporter:
    def __init__(self) -> None:
        self.command: ImportAttendancesCommand | None = None

    def execute(self, command: ImportAttendancesCommand) -> ImportAttendancesResult:
        self.command = command
        return ImportAttendancesResult(
            len(command.attendances), len(command.attendances), 0, ()
        )


def test_csv_preserves_classification_identity_and_timezone() -> None:
    importer = CapturingImporter()
    result = AttendanceCsvImportService(importer).import_csv(
        HEADER
        + "attendance-1,protocol-1,local,customer-1,operator-1,phone,"
        "2026-07-20T12:00:00-03:00,01,Atendimento Suporte,030,Link PG Cartão,"
        "001,Dispositivo Cliente\n"
    )

    assert result.created_count == 1
    assert importer.command is not None
    item = importer.command.attendances[0]
    assert item.opening_classification.code == "030"
    assert item.opening_classification.description == "Link PG Cartão"
    assert item.occurred_at.utcoffset() == -timedelta(hours=3)


def test_csv_supports_classification_without_code() -> None:
    importer = CapturingImporter()
    AttendanceCsvImportService(importer).import_csv(
        HEADER
        + "attendance-1,protocol-1,local,customer-1,operator-1,whatsapp,"
        "2026-07-20T12:00:00Z,01,Atendimento Suporte,,NPS Passivos,"
        "001,Dispositivo Cliente\n"
    )

    assert importer.command is not None
    assert importer.command.attendances[0].opening_classification.code is None


def test_csv_forwards_explicit_coverage_without_deriving_it_from_rows() -> None:
    importer = CapturingImporter()
    coverage = AttendanceCoverageDeclaration(
        source="local",
        covered_through=date(2026, 8, 30),
        import_reference="export-2026-08-30",
    )

    AttendanceCsvImportService(importer).import_csv(
        HEADER,
        coverage=coverage,
    )

    assert importer.command == ImportAttendancesCommand((), coverage)


@pytest.mark.parametrize(
    ("content", "error"),
    [
        ("wrong,header\n1,2\n", AttendanceCsvStructureError),
        (
            HEADER
            + "attendance-1,protocol-1,local,customer-1,operator-1,phone,"
            "2026-07-20T12:00:00,01,Atendimento Suporte,001,Lentidão,"
            "001,Dispositivo Cliente\n",
            AttendanceCsvValidationError,
        ),
        (
            HEADER
            + "attendance-1,protocol-1,local,customer-1,operator-1,phone,"
            "2026-07-20T12:00:00Z,01,Atendimento Suporte,001,Lentidão,"
            "001,Dispositivo Cliente\n"
            + "attendance-1,protocol-2,local,customer-2,operator-2,phone,"
            "2026-07-21T12:00:00Z,01,Atendimento Suporte,001,Lentidão,"
            "001,Dispositivo Cliente\n",
            AttendanceCsvValidationError,
        ),
    ],
)
def test_csv_rejects_invalid_contract(
    content: str, error: type[ValueError]
) -> None:
    with pytest.raises(error):
        AttendanceCsvImportService(CapturingImporter()).import_csv(content)
