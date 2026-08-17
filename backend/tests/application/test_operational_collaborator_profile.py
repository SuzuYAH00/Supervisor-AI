from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import (
    CsatEvaluation,
    OperationalCollaboratorProfile,
    OperationalCollaboratorProfileConflict,
)
from supervisor_ai.application.use_cases import (
    RegisterOperationalCollaboratorProfileCommand,
    RegisterOperationalCollaboratorProfileUseCase,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel


@pytest.mark.parametrize(
    "channel",
    (CsatCompetitiveChannel.CHAT, CsatCompetitiveChannel.PHONE),
)
def test_profile_accepts_each_competitive_channel(
    channel: CsatCompetitiveChannel,
) -> None:
    profile = OperationalCollaboratorProfile("operator-1", channel)

    assert profile.collaborator_id == "operator-1"
    assert profile.competitive_channel is channel


def test_profile_rejects_blank_identity_invalid_channel_and_is_immutable() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        OperationalCollaboratorProfile(" ", CsatCompetitiveChannel.CHAT)
    with pytest.raises(ValueError, match="is not a valid"):
        CsatCompetitiveChannel("email")

    profile = OperationalCollaboratorProfile("operator-1", CsatCompetitiveChannel.CHAT)
    with pytest.raises(FrozenInstanceError):
        profile.collaborator_id = "operator-2"


def test_registration_persists_is_idempotent_and_rejects_implicit_change(
    session_factory: sessionmaker[Session],
) -> None:
    service = RegisterOperationalCollaboratorProfileUseCase(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    )
    command = RegisterOperationalCollaboratorProfileCommand(
        "operator-1", CsatCompetitiveChannel.CHAT
    )

    first = service.execute(command)
    second = service.execute(command)

    assert first.created
    assert not second.created
    assert second.profile == first.profile
    with pytest.raises(OperationalCollaboratorProfileConflict):
        service.execute(
            RegisterOperationalCollaboratorProfileCommand(
                "operator-1", CsatCompetitiveChannel.PHONE
            )
        )
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.operational_collaborators.get_by_id("operator-1") == (
            first.profile
        )


def test_evaluation_channel_does_not_change_competitive_channel(
    session_factory: sessionmaker[Session],
) -> None:
    created_at = datetime(2026, 8, 17, 12, tzinfo=UTC)
    profile = OperationalCollaboratorProfile(
        "operator-1", CsatCompetitiveChannel.CHAT, created_at
    )
    evaluation = CsatEvaluation(
        id="evaluation-1",
        external_reference="external-1",
        source="local-test",
        collaborator_id="operator-1",
        channel="phone",
        score=Decimal("5"),
        evaluated_at=created_at,
        created_at=created_at,
    )
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.operational_collaborators.add(profile)
        unit_of_work.csat.add(evaluation)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        recovered = unit_of_work.operational_collaborators.get_by_id("operator-1")

    assert recovered is not None
    assert recovered.competitive_channel is CsatCompetitiveChannel.CHAT
