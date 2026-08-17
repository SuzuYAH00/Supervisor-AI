from dataclasses import dataclass

from supervisor_ai.application.errors import (
    CollaboratorExternalIdentityConflict,
    OperationalCollaboratorProfileNotFound,
)
from supervisor_ai.application.persistence import CollaboratorExternalIdentity
from supervisor_ai.application.ports import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class RegisterCollaboratorExternalIdentityCommand:
    collaborator_id: str
    source: str
    external_identity: str


@dataclass(frozen=True, slots=True)
class RegisterCollaboratorExternalIdentityResult:
    identity: CollaboratorExternalIdentity
    created: bool


class RegisterCollaboratorExternalIdentityUseCase:
    """Associa uma identidade externa exata a um perfil canônico existente."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, command: RegisterCollaboratorExternalIdentityCommand
    ) -> RegisterCollaboratorExternalIdentityResult:
        requested = CollaboratorExternalIdentity(
            collaborator_id=command.collaborator_id,
            source=command.source,
            external_identity=command.external_identity,
        )
        with self._unit_of_work_factory() as unit_of_work:
            profile = unit_of_work.operational_collaborators.get_by_id(
                requested.collaborator_id
            )
            if profile is None:
                raise OperationalCollaboratorProfileNotFound

            existing = (
                unit_of_work.collaborator_external_identities.get_by_source_identity(
                    source=requested.source,
                    external_identity=requested.external_identity,
                )
            )
            if existing is not None:
                if existing.collaborator_id != requested.collaborator_id:
                    raise CollaboratorExternalIdentityConflict
                return RegisterCollaboratorExternalIdentityResult(
                    identity=existing,
                    created=False,
                )

            unit_of_work.collaborator_external_identities.add(requested)
            unit_of_work.commit()
            return RegisterCollaboratorExternalIdentityResult(
                identity=requested,
                created=True,
            )
