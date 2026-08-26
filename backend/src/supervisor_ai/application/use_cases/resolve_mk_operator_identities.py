from dataclasses import dataclass

from supervisor_ai.application.mk_operational import (
    MK_EXTERNAL_IDENTITY_SOURCE,
    MkOperatorResolutionStatus,
)
from supervisor_ai.application.ports import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class ResolveMkOperatorIdentitiesQuery:
    external_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for external_id in self.external_ids:
            if not external_id.strip():
                raise ValueError("external_ids must not contain blank values")
            if len(external_id) > 255:
                raise ValueError("external_ids must not exceed 255 characters")


@dataclass(frozen=True, slots=True)
class MkOperatorIdentityResolution:
    external_id: str
    collaborator_id: str | None
    status: MkOperatorResolutionStatus


@dataclass(frozen=True, slots=True)
class ResolveMkOperatorIdentitiesResult:
    items: tuple[MkOperatorIdentityResolution, ...]

    @property
    def resolved(self) -> dict[str, str]:
        return {
            item.external_id: item.collaborator_id
            for item in self.items
            if item.collaborator_id is not None
        }

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(
            item.external_id for item in self.items if item.collaborator_id is None
        )


class ResolveMkOperatorIdentitiesUseCase:
    """Resolve usr_codigo exato; nomes e logins nunca criam associação."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, query: ResolveMkOperatorIdentitiesQuery
    ) -> ResolveMkOperatorIdentitiesResult:
        external_ids = tuple(dict.fromkeys(query.external_ids))
        if not external_ids:
            return ResolveMkOperatorIdentitiesResult(())

        with self._unit_of_work_factory() as unit_of_work:
            identities = (
                unit_of_work.collaborator_external_identities.get_by_source_identities(
                    source=MK_EXTERNAL_IDENTITY_SOURCE,
                    external_identities=external_ids,
                )
            )
        by_external_id = {
            identity.external_identity: identity.collaborator_id
            for identity in identities
        }
        return ResolveMkOperatorIdentitiesResult(
            tuple(
                MkOperatorIdentityResolution(
                    external_id=external_id,
                    collaborator_id=by_external_id.get(external_id),
                    status=(
                        MkOperatorResolutionStatus.EXACT_EXTERNAL_ID
                        if external_id in by_external_id
                        else MkOperatorResolutionStatus.MANUAL_MAPPING_REQUIRED
                    ),
                )
                for external_id in external_ids
            )
        )
