from dataclasses import dataclass

from supervisor_ai.application.errors import CollaboratorExternalIdentityNotFound
from supervisor_ai.application.ports import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class ResolveCollaboratorExternalIdentityQuery:
    source: str
    external_identity: str

    def __post_init__(self) -> None:
        values = {
            "source": (self.source, 100),
            "external_identity": (self.external_identity, 255),
        }
        for name, (value, maximum) in values.items():
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")


@dataclass(frozen=True, slots=True)
class ResolveCollaboratorExternalIdentityResult:
    collaborator_id: str
    source: str
    external_identity: str


class ResolveCollaboratorExternalIdentityUseCase:
    """Resolve somente correspondências exatas, sem normalização ou aproximação."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, query: ResolveCollaboratorExternalIdentityQuery
    ) -> ResolveCollaboratorExternalIdentityResult:
        with self._unit_of_work_factory() as unit_of_work:
            identity = (
                unit_of_work.collaborator_external_identities.get_by_source_identity(
                    source=query.source,
                    external_identity=query.external_identity,
                )
            )
            if identity is None:
                raise CollaboratorExternalIdentityNotFound
            return ResolveCollaboratorExternalIdentityResult(
                collaborator_id=identity.collaborator_id,
                source=identity.source,
                external_identity=identity.external_identity,
            )
