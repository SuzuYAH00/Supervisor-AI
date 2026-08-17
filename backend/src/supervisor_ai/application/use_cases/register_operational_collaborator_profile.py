from dataclasses import dataclass

from supervisor_ai.application.errors import (
    OperationalCollaboratorProfileConflict,
)
from supervisor_ai.application.persistence import OperationalCollaboratorProfile
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.rules_engine import CsatCompetitiveChannel


@dataclass(frozen=True, slots=True)
class RegisterOperationalCollaboratorProfileCommand:
    collaborator_id: str
    competitive_channel: CsatCompetitiveChannel


@dataclass(frozen=True, slots=True)
class RegisterOperationalCollaboratorProfileResult:
    profile: OperationalCollaboratorProfile
    created: bool


class RegisterOperationalCollaboratorProfileUseCase:
    """Registra a configuração factual sem inferi-la de avaliações."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, command: RegisterOperationalCollaboratorProfileCommand
    ) -> RegisterOperationalCollaboratorProfileResult:
        requested = OperationalCollaboratorProfile(
            collaborator_id=command.collaborator_id,
            competitive_channel=command.competitive_channel,
        )
        with self._unit_of_work_factory() as unit_of_work:
            existing = unit_of_work.operational_collaborators.get_by_id(
                requested.collaborator_id
            )
            if existing is not None:
                if existing.competitive_channel is not requested.competitive_channel:
                    raise OperationalCollaboratorProfileConflict
                return RegisterOperationalCollaboratorProfileResult(
                    profile=existing,
                    created=False,
                )
            unit_of_work.operational_collaborators.add(requested)
            unit_of_work.commit()
            return RegisterOperationalCollaboratorProfileResult(
                profile=requested,
                created=True,
            )
