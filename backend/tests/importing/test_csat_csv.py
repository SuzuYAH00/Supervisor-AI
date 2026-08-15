from datetime import timedelta
from decimal import Decimal

import pytest

from supervisor_ai.application.use_cases import (
    ImportCsatEvaluationsCommand,
    ImportCsatEvaluationsResult,
)
from supervisor_ai.infrastructure.importing import (
    CsatCsvImportService,
    CsatCsvStructureError,
    CsatCsvValidationError,
)

HEADER = (
    "evaluation_id,external_reference,source,collaborator_id,channel,score,"
    "evaluated_at\n"
)


class CapturingImporter:
    def __init__(self) -> None:
        self.command: ImportCsatEvaluationsCommand | None = None

    def execute(
        self, command: ImportCsatEvaluationsCommand
    ) -> ImportCsatEvaluationsResult:
        self.command = command
        return ImportCsatEvaluationsResult(
            len(command.evaluations), len(command.evaluations), 0, ()
        )


def test_csv_contract_preserves_decimal_timezone_source_and_optional_channel() -> None:
    importer = CapturingImporter()
    service = CsatCsvImportService(importer)
    result = service.import_csv(
        HEADER
        + "csat-1,external-1,mkbot-export,collaborator-1,,9.50,"
        "2026-07-20T12:00:00-03:00\n"
    )

    assert result.created_count == 1
    assert importer.command is not None
    item = importer.command.evaluations[0]
    assert item.score == Decimal("9.50")
    assert item.channel is None
    assert item.evaluated_at.isoformat() == "2026-07-20T12:00:00-03:00"
    assert item.evaluated_at.utcoffset() == -timedelta(hours=3)


@pytest.mark.parametrize(
    "content,error_type",
    [
        ("wrong,header\n1,2\n", CsatCsvStructureError),
        (
            HEADER + "csat-1,ref,source,user,chat,NaN,2026-07-20T12:00:00Z\n",
            CsatCsvValidationError,
        ),
        (
            HEADER + "csat-1,ref,source,user,chat,10,2026-07-20T12:00:00\n",
            CsatCsvValidationError,
        ),
        (
            HEADER
            + "csat-1,ref,source,user,chat,10,2026-07-20T12:00:00Z\n"
            + "csat-1,ref-2,source,user,chat,9,2026-07-20T12:01:00Z\n",
            CsatCsvValidationError,
        ),
    ],
)
def test_csv_rejects_invalid_contracts(
    content: str, error_type: type[ValueError]
) -> None:
    with pytest.raises(error_type):
        CsatCsvImportService(CapturingImporter()).import_csv(content)
