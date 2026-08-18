from datetime import UTC, date, datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application.use_cases import (
    ImportEmployeeOccurrenceReportsUseCase,
    RegisterCollaboratorExternalIdentityCommand,
    RegisterCollaboratorExternalIdentityUseCase,
    RegisterOperationalCollaboratorProfileCommand,
    RegisterOperationalCollaboratorProfileUseCase,
)
from supervisor_ai.infrastructure.importing import (
    EMPLOYEE_OCCURRENCE_SOURCE,
    EmployeeOccurrenceXlsxImportService,
    parse_employee_occurrence_xlsx,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel

NOW = datetime(2026, 8, 18, 18, tzinfo=UTC)


def _xlsx(rows: tuple[tuple[str, str, str, str, str], ...]) -> bytes:
    output = BytesIO()
    headers = (
        "Carimbo de data/hora",
        "Técnico de Suporte",
        "Data - (DD/MM/AA)",
        "Motivo Ocorrência",
        "Pontuação",
    )
    xml_rows = []
    for row_number, values in enumerate((headers, *rows), start=1):
        cells = "".join(
            f'<c r="{column}{row_number}" t="inlineStr"><is><t>{value}</t></is></c>'
            for column, value in zip("ABCDE", values, strict=True)
        )
        xml_rows.append(f'<row r="{row_number}">{cells}</row>')
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><workbook '
            'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Respostas ao formulário 1" sheetId="1" '
            'r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0"?><Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0"?><worksheet '
            'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{''.join(xml_rows)}</sheetData></worksheet>",
        )
    return output.getvalue()


def _row(
    *,
    timestamp: str = "46252.5",
    identity: str = "Agent One",
    occurrence_date: str = "18/08/26",
    reason: str = "Falha interna declarada",
) -> tuple[str, str, str, str, str]:
    return timestamp, identity, occurrence_date, reason, "0"


def _prepare(session_factory: sessionmaker[Session]) -> None:
    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    RegisterOperationalCollaboratorProfileUseCase(factory).execute(
        RegisterOperationalCollaboratorProfileCommand(
            "collaborator-1", CsatCompetitiveChannel.CHAT
        )
    )
    RegisterCollaboratorExternalIdentityUseCase(factory).execute(
        RegisterCollaboratorExternalIdentityCommand(
            "collaborator-1", EMPLOYEE_OCCURRENCE_SOURCE, "Agent One"
        )
    )


def _service(
    session_factory: sessionmaker[Session],
) -> EmployeeOccurrenceXlsxImportService:
    return EmployeeOccurrenceXlsxImportService(
        ImportEmployeeOccurrenceReportsUseCase(
            lambda: SqlAlchemyUnitOfWork(session_factory), lambda: NOW
        )
    )


def test_parser_accepts_only_normative_dates_and_applies_operational_timezone() -> None:
    parsed = parse_employee_occurrence_xlsx(
        _xlsx(
            (
                _row(occurrence_date="18/08/26"),
                _row(timestamp="46252.6", occurrence_date="19/08/2026"),
                _row(timestamp="46252.7", occurrence_date="18/08"),
                _row(timestamp="46252.8", occurrence_date="18/08/2026 08:00"),
            )
        )
    )

    assert parsed.total_data_rows == 4
    assert [report.occurrence_date for report in parsed.reports] == [
        date(2026, 8, 18),
        date(2026, 8, 19),
    ]
    assert parsed.reports[0].submitted_at.utcoffset().total_seconds() == -10800
    assert [issue.code for issue in parsed.issues] == [
        "invalid_occurrence_date",
        "invalid_occurrence_date",
    ]


def test_partial_import_reports_invalid_and_unknown_rows(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare(session_factory)

    result = _service(session_factory).import_xlsx(
        _xlsx(
            (
                _row(),
                _row(timestamp="46252.6", occurrence_date="18-08-2026"),
                _row(timestamp="46252.7", identity="AgentOne"),
            )
        )
    )

    assert (
        result.total_data_rows,
        result.imported_rows,
        result.idempotent_rows,
        result.rejected_rows,
        result.conflict_rows,
    ) == (3, 1, 0, 2, 0)
    assert [issue.code for issue in result.issues] == [
        "invalid_occurrence_date",
        "unknown_collaborator_alias",
    ]


def test_reimport_is_idempotent_and_changed_fact_conflicts_without_overwrite(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare(session_factory)
    service = _service(session_factory)

    first = service.import_xlsx(_xlsx((_row(),)))
    second = service.import_xlsx(_xlsx((_row(),)))
    conflict = service.import_xlsx(_xlsx((_row(reason="Outro fato declarado"),)))

    assert (first.imported_rows, first.idempotent_rows) == (1, 0)
    assert (second.imported_rows, second.idempotent_rows) == (0, 1)
    assert (conflict.imported_rows, conflict.conflict_rows) == (0, 1)
    assert conflict.issues[0].code == "conflicting_occurrence"
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        persisted = unit_of_work.employee_occurrence_reports.get_by_source_reference(
            source=EMPLOYEE_OCCURRENCE_SOURCE,
            external_reference=parse_employee_occurrence_xlsx(_xlsx((_row(),)))
            .reports[0]
            .external_reference,
        )
        reports_for_review = (
            unit_of_work.employee_occurrence_reports.search_by_collaborator_date(
                collaborator_id="collaborator-1",
                occurrence_date=date(2026, 8, 18),
            )
        )
    assert persisted is not None
    assert persisted.reason_text == "Falha interna declarada"
    assert reports_for_review == (persisted,)


def test_report_contract_is_immutable_and_does_not_model_review_decision() -> None:
    report = parse_employee_occurrence_xlsx(_xlsx((_row(),))).reports[0]

    assert not hasattr(report, "decision")
    assert not hasattr(report, "delay_occurrence_id")
