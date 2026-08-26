from dataclasses import replace
from datetime import UTC, datetime

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import (
    MK_EXTERNAL_IDENTITY_SOURCE,
    CollaboratorExternalIdentityConflict,
    MkAttendanceMirror,
    MkOperatorResolutionStatus,
    mk_user_external_identity,
)
from supervisor_ai.application.use_cases import (
    RegisterCollaboratorExternalIdentityCommand,
    RegisterCollaboratorExternalIdentityUseCase,
    RegisterOperationalCollaboratorProfileCommand,
    RegisterOperationalCollaboratorProfileUseCase,
    ResolveMkOperatorIdentitiesQuery,
    ResolveMkOperatorIdentitiesUseCase,
)
from supervisor_ai.infrastructure.external.mk import MkUser
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel

NOW = datetime(2026, 8, 26, 12, tzinfo=UTC)


def _factory(session_factory: sessionmaker[Session]):
    return lambda: SqlAlchemyUnitOfWork(session_factory)


def _profile(session_factory: sessionmaker[Session], collaborator_id: str) -> None:
    RegisterOperationalCollaboratorProfileUseCase(_factory(session_factory)).execute(
        RegisterOperationalCollaboratorProfileCommand(
            collaborator_id, CsatCompetitiveChannel.CHAT
        )
    )


def _map(
    session_factory: sessionmaker[Session], collaborator_id: str, user_id: int
) -> None:
    RegisterCollaboratorExternalIdentityUseCase(_factory(session_factory)).execute(
        RegisterCollaboratorExternalIdentityCommand(
            collaborator_id=collaborator_id,
            source=MK_EXTERNAL_IDENTITY_SOURCE,
            external_identity=mk_user_external_identity(user_id),
        )
    )


def test_batch_resolves_exact_usr_codigo_and_reports_unresolved_once(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "collaborator-fixture")
    _map(session_factory, "collaborator-fixture", 1788)
    engine = session_factory.kw["bind"]
    identity_selects: list[str] = []

    def observe(_conn, _cursor, statement, _parameters, _context, _many) -> None:
        if statement.lstrip().upper().startswith("SELECT") and (
            "collaborator_external_identities" in statement
        ):
            identity_selects.append(statement)

    event.listen(engine, "before_cursor_execute", observe)
    try:
        result = ResolveMkOperatorIdentitiesUseCase(_factory(session_factory)).execute(
            ResolveMkOperatorIdentitiesQuery(("1788", "9999", "1788"))
        )
    finally:
        event.remove(engine, "before_cursor_execute", observe)

    assert result.resolved == {"1788": "collaborator-fixture"}
    assert result.unresolved == ("9999",)
    assert [item.external_id for item in result.items] == ["1788", "9999"]
    assert result.items[0].status is MkOperatorResolutionStatus.EXACT_EXTERNAL_ID
    assert result.items[1].status is MkOperatorResolutionStatus.MANUAL_MAPPING_REQUIRED
    assert len(identity_selects) == 1


def test_empty_batch_does_not_open_unit_of_work() -> None:
    calls = 0

    def factory():
        nonlocal calls
        calls += 1
        raise AssertionError("empty resolution must not open a unit of work")

    result = ResolveMkOperatorIdentitiesUseCase(factory).execute(
        ResolveMkOperatorIdentitiesQuery(())
    )
    assert result.items == ()
    assert result.resolved == {}
    assert result.unresolved == ()
    assert calls == 0


def test_name_and_login_changes_do_not_change_usr_codigo_identity(
    session_factory: sessionmaker[Session],
) -> None:
    original = MkUser(1788, "operator.fixture", "Operador Fictício")
    renamed = replace(
        original,
        login="renamed.fixture",
        name="Nome Fictício Alterado",
    )
    assert mk_user_external_identity(original.user_id) == "1788"
    assert mk_user_external_identity(renamed.user_id) == "1788"

    _profile(session_factory, "collaborator-fixture")
    _map(session_factory, "collaborator-fixture", original.user_id)
    result = ResolveMkOperatorIdentitiesUseCase(_factory(session_factory)).execute(
        ResolveMkOperatorIdentitiesQuery((mk_user_external_identity(renamed.user_id),))
    )
    assert result.resolved == {"1788": "collaborator-fixture"}


def test_same_mk_usr_codigo_cannot_map_to_two_collaborators(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "collaborator-a")
    _profile(session_factory, "collaborator-b")
    _map(session_factory, "collaborator-a", 1788)
    with pytest.raises(CollaboratorExternalIdentityConflict):
        _map(session_factory, "collaborator-b", 1788)


def test_unknown_operator_remains_in_mirror_and_resolves_after_mapping(
    session_factory: sessionmaker[Session],
) -> None:
    mirror = MkAttendanceMirror(
        external_id="attendance-fixture",
        protocol="2699.10180",
        customer_external_id="customer-fixture",
        opened_at=NOW,
        closed_at=None,
        opening_operator_external_id="1788",
        closing_operator_external_id=None,
        process_external_id=None,
        subprocess_external_id=None,
        opening_classification_external_id=None,
        closing_classification_external_id=None,
        origin_external_id=None,
        status="open",
        is_finalized=False,
        mk_dialog_session_external_id=None,
        source_first_seen_at=NOW,
        source_last_seen_at=NOW,
        local_created_at=NOW,
        local_updated_at=NOW,
    )
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.mk_attendances.upsert(mirror)
        unit_of_work.commit()

    before = ResolveMkOperatorIdentitiesUseCase(_factory(session_factory)).execute(
        ResolveMkOperatorIdentitiesQuery(("1788",))
    )
    assert before.unresolved == ("1788",)

    _profile(session_factory, "collaborator-fixture")
    _map(session_factory, "collaborator-fixture", 1788)
    after = ResolveMkOperatorIdentitiesUseCase(_factory(session_factory)).execute(
        ResolveMkOperatorIdentitiesQuery(("1788",))
    )
    assert after.resolved == {"1788": "collaborator-fixture"}
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        persisted = unit_of_work.mk_attendances.get_by_external_id("attendance-fixture")
        assert persisted is not None
        assert persisted.opening_operator_external_id == "1788"
