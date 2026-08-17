from datetime import UTC, date, datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import CollaboratorExternalIdentityNotFound
from supervisor_ai.application.use_cases import (
    ImportDailyWorkStatusesUseCase,
    RegisterCollaboratorExternalIdentityCommand,
    RegisterCollaboratorExternalIdentityUseCase,
    RegisterOperationalCollaboratorProfileCommand,
    RegisterOperationalCollaboratorProfileUseCase,
)
from supervisor_ai.infrastructure.importing import (
    WorkforceScheduleXlsxError,
    WorkforceScheduleXlsxImportService,
    parse_workforce_schedule_xlsx,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel


def _xlsx(
    *, month: str = "ABRIL", year: int = 2026, identity: str = "Agent One"
) -> bytes:
    output = BytesIO()
    sheet_name = f"ESCALA - {month} {year}"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><workbook '
            'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0"?><Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0"?><worksheet '
            'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            '<row r="1"><c r="B1"><v>46113</v></c><c r="C1"><v>46114</v></c>'
            '<c r="D1"><v>46112</v></c></row>'
            f'<row r="3"><c r="A3" t="inlineStr"><is><t>{identity}</t></is></c>'
            '<c r="B3" t="inlineStr"><is><t>P</t></is></c>'
            '<c r="C3" t="inlineStr"><is><t>B.H</t></is></c>'
            '<c r="D3" t="inlineStr"><is><t>F</t></is></c></row>'
            "</sheetData>"
            '<dataValidations count="1"><dataValidation type="list" sqref="B3:D3"/>'
            "</dataValidations></worksheet>",
        )
    return output.getvalue()


def _prepare(session_factory: sessionmaker[Session]) -> None:
    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    RegisterOperationalCollaboratorProfileUseCase(factory).execute(
        RegisterOperationalCollaboratorProfileCommand(
            "collaborator-1", CsatCompetitiveChannel.PHONE
        )
    )
    RegisterCollaboratorExternalIdentityUseCase(factory).execute(
        RegisterCollaboratorExternalIdentityCommand(
            "collaborator-1", "attendance_sheet", "Agent One"
        )
    )


def test_parser_uses_cell_dates_and_ignores_dates_outside_sheet_month() -> None:
    facts = parse_workforce_schedule_xlsx(_xlsx())

    assert [(fact.work_date, fact.raw_code) for fact in facts] == [
        (date(2026, 4, 1), "P"),
        (date(2026, 4, 2), "B.H"),
    ]
    assert all(fact.competence_month == date(2026, 4, 1) for fact in facts)


def test_parser_rejects_pre_april_only_workbook() -> None:
    with pytest.raises(WorkforceScheduleXlsxError, match="April 2026"):
        parse_workforce_schedule_xlsx(_xlsx(month="MARÇO"))


def test_service_resolves_alias_and_reimport_does_not_duplicate(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare(session_factory)
    service = WorkforceScheduleXlsxImportService(
        ImportDailyWorkStatusesUseCase(
            lambda: SqlAlchemyUnitOfWork(session_factory),
            lambda: datetime(2026, 8, 17, tzinfo=UTC),
        )
    )

    first = service.import_xlsx(_xlsx())
    second = service.import_xlsx(_xlsx())

    assert (first.created_count, first.received_count) == (2, 2)
    assert (second.created_count, second.already_existing_count) == (0, 2)


def test_service_rejects_unmapped_identity_without_fuzzy_matching(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare(session_factory)
    service = WorkforceScheduleXlsxImportService(
        ImportDailyWorkStatusesUseCase(
            lambda: SqlAlchemyUnitOfWork(session_factory),
            lambda: datetime(2026, 8, 17, tzinfo=UTC),
        )
    )

    with pytest.raises(CollaboratorExternalIdentityNotFound):
        service.import_xlsx(_xlsx(identity="AgentOne"))
