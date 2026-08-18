from datetime import UTC, datetime
from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import (
    CollaboratorExternalIdentityNotFound,
    CsatContactConflict,
)
from supervisor_ai.application.use_cases import (
    ImportCsatContactsUseCase,
    RegisterCollaboratorExternalIdentityCommand,
    RegisterCollaboratorExternalIdentityUseCase,
    RegisterOperationalCollaboratorProfileCommand,
    RegisterOperationalCollaboratorProfileUseCase,
)
from supervisor_ai.infrastructure.importing import (
    MK_CSAT_SOURCE,
    NPX_CSAT_SOURCE,
    MkCsatXlsxImportService,
    NpxCsatXlsxImportService,
    parse_mk_csat_xlsx,
    parse_npx_csat_xlsx,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel

MK_HEADER = (
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
NPX_HEADER = (
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
NOW = datetime(2026, 8, 18, tzinfo=UTC)


def _xlsx(rows: tuple[tuple[str, ...], ...]) -> bytes:
    output = BytesIO()
    sheet_rows = []
    for row_number, values in enumerate(rows, start=1):
        cells = "".join(
            f'<c r="{chr(64 + column)}{row_number}" t="inlineStr">'
            f"<is><t>{escape(value)}</t></is></c>"
            for column, value in enumerate(values, start=1)
        )
        sheet_rows.append(f'<row r="{row_number}">{cells}</row>')
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><workbook '
            'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
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
            f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>",
        )
    return output.getvalue()


def _mk_row(
    score: str,
    protocol: str,
    *,
    operator: str = "Agent One",
    sector: str = "Assuntos Financeiros",
    contact: str = "contact-1",
) -> tuple[str, ...]:
    return (
        score,
        "05/08/2026 22:50:57",
        "19 min",
        sector,
        operator,
        "WhatsApp-channel",
        "Customer",
        "10 min",
        "1 min",
        protocol,
        contact,
    )


def _npx_row(
    linked_id: str,
    p1: str,
    p2: str,
    p3: str,
    *,
    agent: str = "Agent Phone",
) -> tuple[str, ...]:
    return (
        "001",
        agent,
        "05/08/2026",
        "phone",
        "00:05:00",
        "00:00:05",
        linked_id,
        p1,
        p2,
        p3,
        "",
    )


def _prepare(
    session_factory: sessionmaker[Session],
    collaborator_id: str,
    channel: CsatCompetitiveChannel,
    source: str,
    identity: str,
) -> None:
    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    RegisterOperationalCollaboratorProfileUseCase(factory).execute(
        RegisterOperationalCollaboratorProfileCommand(collaborator_id, channel)
    )
    RegisterCollaboratorExternalIdentityUseCase(factory).execute(
        RegisterCollaboratorExternalIdentityCommand(
            collaborator_id, source, identity
        )
    )


def test_mk_parser_models_unanswered_zero_five_and_excludes_bot() -> None:
    contacts = parse_mk_csat_xlsx(
        _xlsx(
            (
                MK_HEADER,
                _mk_row("-1", "protocol-1"),
                _mk_row("0", "protocol-2", contact="same-customer"),
                _mk_row("5", "protocol-3", contact="same-customer"),
                _mk_row("-1", "bot-protocol", operator=" MKBOT assistant"),
            )
        )
    )

    assert [item.external_reference for item in contacts] == [
        "protocol-1",
        "protocol-2",
        "protocol-3",
    ]
    assert [item.score for item in contacts] == [None, 0, 5]
    assert all(
        item.source_channel is CsatCompetitiveChannel.CHAT for item in contacts
    )


def test_mk_financial_and_technical_use_one_source_population() -> None:
    financial = parse_mk_csat_xlsx(
        _xlsx((MK_HEADER, _mk_row("5", "financial-1")))
    )
    technical = parse_mk_csat_xlsx(
        _xlsx(
            (
                MK_HEADER,
                _mk_row(
                    "5",
                    "technical-1",
                    sector="Assuntos Técnicos",
                ),
            )
        )
    )

    assert {item.source for item in financial + technical} == {MK_CSAT_SOURCE}
    assert {item.source_context for item in financial + technical} == {
        "Assuntos Financeiros",
        "Assuntos Técnicos",
    }


def test_npx_parser_uses_p2_and_models_x_triplet_as_unanswered() -> None:
    contacts = parse_npx_csat_xlsx(
        _xlsx(
            (
                ("NPX",),
                NPX_HEADER,
                _npx_row("linked-1", "x", "x", "x"),
                _npx_row("linked-2", "other", "1", "ignored"),
                _npx_row("linked-3", "different", "5", "also-ignored"),
            )
        )
    )

    assert [item.score for item in contacts] == [None, 1, 5]
    assert [item.external_reference for item in contacts] == [
        "linked-1",
        "linked-2",
        "linked-3",
    ]
    assert all(
        item.source_channel is CsatCompetitiveChannel.PHONE for item in contacts
    )


def test_services_resolve_exact_alias_and_reimport_idempotently(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare(
        session_factory,
        "chat-collaborator",
        CsatCompetitiveChannel.CHAT,
        MK_CSAT_SOURCE,
        "Agent One",
    )
    service = MkCsatXlsxImportService(
        ImportCsatContactsUseCase(
            lambda: SqlAlchemyUnitOfWork(session_factory), lambda: NOW
        )
    )
    content = _xlsx((MK_HEADER, _mk_row("5", "protocol-1")))

    first = service.import_xlsx(content)
    second = service.import_xlsx(content)

    assert (first.received_count, first.created_count) == (1, 1)
    assert (second.created_count, second.already_existing_count) == (0, 1)


def test_missing_alias_is_not_resolved_by_similarity(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare(
        session_factory,
        "chat-collaborator",
        CsatCompetitiveChannel.CHAT,
        MK_CSAT_SOURCE,
        "AgentOne",
    )
    service = MkCsatXlsxImportService(
        ImportCsatContactsUseCase(
            lambda: SqlAlchemyUnitOfWork(session_factory), lambda: NOW
        )
    )

    with pytest.raises(CollaboratorExternalIdentityNotFound):
        service.import_xlsx(
            _xlsx((MK_HEADER, _mk_row("5", "protocol-1")))
        )


def test_npx_reimport_ignores_p1_p3_semantics_but_preserves_p2_score(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare(
        session_factory,
        "phone-collaborator",
        CsatCompetitiveChannel.PHONE,
        NPX_CSAT_SOURCE,
        "Agent Phone",
    )
    service = NpxCsatXlsxImportService(
        ImportCsatContactsUseCase(
            lambda: SqlAlchemyUnitOfWork(session_factory), lambda: NOW
        )
    )

    first = service.import_xlsx(
        _xlsx(
            (
                ("NPX",),
                NPX_HEADER,
                _npx_row("linked-1", "1", "5", "10"),
            )
        )
    )
    second = service.import_xlsx(
        _xlsx(
            (
                ("NPX",),
                NPX_HEADER,
                _npx_row("linked-1", "ignored", "5", "also-ignored"),
            )
        )
    )

    assert first.created_count == 1
    assert (second.created_count, second.already_existing_count) == (0, 1)


def test_same_source_reference_with_different_score_is_conflict(
    session_factory: sessionmaker[Session],
) -> None:
    _prepare(
        session_factory,
        "chat-collaborator",
        CsatCompetitiveChannel.CHAT,
        MK_CSAT_SOURCE,
        "Agent One",
    )
    service = MkCsatXlsxImportService(
        ImportCsatContactsUseCase(
            lambda: SqlAlchemyUnitOfWork(session_factory), lambda: NOW
        )
    )
    service.import_xlsx(_xlsx((MK_HEADER, _mk_row("5", "protocol-1"))))

    with pytest.raises(CsatContactConflict):
        service.import_xlsx(
            _xlsx((MK_HEADER, _mk_row("4", "protocol-1")))
        )
