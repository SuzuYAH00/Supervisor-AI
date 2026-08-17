from dataclasses import FrozenInstanceError

import pytest
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import (
    CollaboratorExternalIdentity,
    CollaboratorExternalIdentityConflict,
    CollaboratorExternalIdentityNotFound,
    OperationalCollaboratorProfileNotFound,
)
from supervisor_ai.application.use_cases import (
    RegisterCollaboratorExternalIdentityCommand,
    RegisterCollaboratorExternalIdentityUseCase,
    RegisterOperationalCollaboratorProfileCommand,
    RegisterOperationalCollaboratorProfileUseCase,
    ResolveCollaboratorExternalIdentityQuery,
    ResolveCollaboratorExternalIdentityUseCase,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel


def _profile(
    session_factory: sessionmaker[Session], collaborator_id: str
) -> None:
    RegisterOperationalCollaboratorProfileUseCase(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    ).execute(
        RegisterOperationalCollaboratorProfileCommand(
            collaborator_id,
            CsatCompetitiveChannel.CHAT,
        )
    )


def _register(
    session_factory: sessionmaker[Session],
    *,
    collaborator_id: str,
    source: str,
    external_identity: str,
) -> bool:
    result = RegisterCollaboratorExternalIdentityUseCase(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    ).execute(
        RegisterCollaboratorExternalIdentityCommand(
            collaborator_id=collaborator_id,
            source=source,
            external_identity=external_identity,
        )
    )
    return result.created


def _resolve(
    session_factory: sessionmaker[Session],
    *,
    source: str,
    external_identity: str,
) -> str:
    result = ResolveCollaboratorExternalIdentityUseCase(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    ).execute(
        ResolveCollaboratorExternalIdentityQuery(
            source=source,
            external_identity=external_identity,
        )
    )
    return result.collaborator_id


def test_registers_and_resolves_multiple_exact_identities(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "collaborator-1")

    assert _register(
        session_factory,
        collaborator_id="collaborator-1",
        source="mk",
        external_identity="Agent One - SUP",
    )
    assert _register(
        session_factory,
        collaborator_id="collaborator-1",
        source="npx",
        external_identity="AgentOne",
    )

    assert (
        _resolve(
            session_factory,
            source="mk",
            external_identity="Agent One - SUP",
        )
        == "collaborator-1"
    )
    assert (
        _resolve(
            session_factory,
            source="npx",
            external_identity="AgentOne",
        )
        == "collaborator-1"
    )


def test_same_external_text_is_independent_between_sources(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "collaborator-a")
    _profile(session_factory, "collaborator-b")

    _register(
        session_factory,
        collaborator_id="collaborator-a",
        source="mk",
        external_identity="123",
    )
    _register(
        session_factory,
        collaborator_id="collaborator-b",
        source="npx",
        external_identity="123",
    )

    assert _resolve(session_factory, source="mk", external_identity="123") == (
        "collaborator-a"
    )
    assert _resolve(session_factory, source="npx", external_identity="123") == (
        "collaborator-b"
    )


def test_registration_is_idempotent_but_rejects_ambiguous_association(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "collaborator-a")
    _profile(session_factory, "collaborator-b")
    command = {
        "source": "npx",
        "external_identity": "AgentOne",
    }

    assert _register(
        session_factory,
        collaborator_id="collaborator-a",
        **command,
    )
    assert not _register(
        session_factory,
        collaborator_id="collaborator-a",
        **command,
    )
    with pytest.raises(CollaboratorExternalIdentityConflict):
        _register(
            session_factory,
            collaborator_id="collaborator-b",
            **command,
        )


def test_registration_requires_existing_canonical_profile(
    session_factory: sessionmaker[Session],
) -> None:
    with pytest.raises(OperationalCollaboratorProfileNotFound):
        _register(
            session_factory,
            collaborator_id="missing-profile",
            source="npx",
            external_identity="AgentOne",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("collaborator_id", " "),
        ("source", " "),
        ("external_identity", " "),
    ),
)
def test_identity_rejects_blank_fields(field: str, value: str) -> None:
    values = {
        "collaborator_id": "collaborator-1",
        "source": "npx",
        "external_identity": "AgentOne",
    }
    values[field] = value

    with pytest.raises(ValueError, match=field):
        CollaboratorExternalIdentity(**values)


def test_contracts_are_immutable() -> None:
    identity = CollaboratorExternalIdentity(
        "collaborator-1", "npx", "AgentOne"
    )
    query = ResolveCollaboratorExternalIdentityQuery("npx", "AgentOne")

    with pytest.raises(FrozenInstanceError):
        identity.external_identity = "AgentTwo"
    with pytest.raises(FrozenInstanceError):
        query.source = "mk"


def test_resolution_is_exact_and_does_not_apply_fuzzy_matching(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "collaborator-1")
    _register(
        session_factory,
        collaborator_id="collaborator-1",
        source="NPX",
        external_identity="AgentOne",
    )

    for source, external_identity in (
        ("NPX", "Agent One"),
        ("npx", "AgentOne"),
        ("NPX", "agentone"),
    ):
        with pytest.raises(CollaboratorExternalIdentityNotFound):
            _resolve(
                session_factory,
                source=source,
                external_identity=external_identity,
            )


def test_identity_preserves_whitespace_and_case_exactly(
    session_factory: sessionmaker[Session],
) -> None:
    _profile(session_factory, "collaborator-1")
    _register(
        session_factory,
        collaborator_id="collaborator-1",
        source="Source A",
        external_identity=" Agent  One ",
    )

    assert (
        _resolve(
            session_factory,
            source="Source A",
            external_identity=" Agent  One ",
        )
        == "collaborator-1"
    )
    with pytest.raises(CollaboratorExternalIdentityNotFound):
        _resolve(
            session_factory,
            source="Source A",
            external_identity="Agent One",
        )
