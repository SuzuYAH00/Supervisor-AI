from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256

from supervisor_ai.application.errors import (
    CollaboratorExternalIdentityNotFound,
    CsatContactConflict,
)
from supervisor_ai.application.persistence import CsatContact
from supervisor_ai.application.ports import Clock, UnitOfWork, UnitOfWorkFactory
from supervisor_ai.rules_engine import CsatCompetitiveChannel


@dataclass(frozen=True, slots=True)
class CsatContactInput:
    external_reference: str
    source: str
    external_operator_identity: str
    occurred_on: date
    source_channel: CsatCompetitiveChannel
    score: Decimal | None
    source_context: str | None = None

    def __post_init__(self) -> None:
        _validate_text(self.external_reference, "external_reference", 255)
        _validate_text(self.source, "source", 100)
        _validate_text(
            self.external_operator_identity,
            "external_operator_identity",
            255,
        )
        if self.source_context is not None:
            _validate_text(self.source_context, "source_context", 255)
        if not isinstance(self.source_channel, CsatCompetitiveChannel):
            raise ValueError("source_channel must be chat or phone")
        if self.score is not None:
            if not self.score.is_finite():
                raise ValueError("score is outside the source scale")
            _, digits, exponent = self.score.as_tuple()
            decimal_places = max(-exponent, 0)
            integer_places = max(len(digits) + exponent, 0)
            minimum = (
                Decimal("0")
                if self.source_channel is CsatCompetitiveChannel.CHAT
                else Decimal("1")
            )
            if (
                decimal_places > 6
                or integer_places > 14
                or not minimum <= self.score <= 5
            ):
                raise ValueError("score is outside the source scale")


@dataclass(frozen=True, slots=True)
class ImportCsatContactsCommand:
    contacts: tuple[CsatContactInput, ...]


@dataclass(frozen=True, slots=True)
class ImportCsatContactsResult:
    received_count: int
    created_count: int
    already_existing_count: int
    contact_ids: tuple[str, ...]


class ImportCsatContactsUseCase:
    def __init__(
        self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(
        self, command: ImportCsatContactsCommand
    ) -> ImportCsatContactsResult:
        created_at = self._clock()
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("clock must return timezone-aware datetimes")
        created_count = 0
        contact_ids: list[str] = []
        with self._unit_of_work_factory() as unit_of_work:
            for item in command.contacts:
                identity = (
                    unit_of_work.collaborator_external_identities.get_by_source_identity(
                        source=item.source,
                        external_identity=item.external_operator_identity,
                    )
                )
                if identity is None:
                    raise CollaboratorExternalIdentityNotFound(
                        "CSAT operator identity has no canonical association: "
                        f"source={item.source!r}, "
                        f"external_identity={item.external_operator_identity!r}"
                    )
                contact = CsatContact(
                    id=_contact_id(item.source, item.external_reference),
                    external_reference=item.external_reference,
                    source=item.source,
                    collaborator_id=identity.collaborator_id,
                    external_operator_identity=item.external_operator_identity,
                    occurred_on=item.occurred_on,
                    source_channel=item.source_channel,
                    score=item.score,
                    source_context=item.source_context,
                    created_at=created_at,
                )
                contact_ids.append(contact.id)
                if self._ensure_contact(unit_of_work, contact):
                    created_count += 1
            unit_of_work.commit()
        return ImportCsatContactsResult(
            received_count=len(command.contacts),
            created_count=created_count,
            already_existing_count=len(command.contacts) - created_count,
            contact_ids=tuple(contact_ids),
        )

    @staticmethod
    def _ensure_contact(unit_of_work: UnitOfWork, contact: CsatContact) -> bool:
        existing = unit_of_work.csat_contacts.get_by_source_reference(
            source=contact.source,
            external_reference=contact.external_reference,
        )
        if existing is None:
            unit_of_work.csat_contacts.add(contact)
            return True
        if not _same_contact(existing, contact):
            raise CsatContactConflict(
                "CSAT contact identity differs from persisted facts"
            )
        return False


def _contact_id(source: str, external_reference: str) -> str:
    digest = sha256(f"{source}\0{external_reference}".encode()).hexdigest()
    return f"csat-contact-{digest}"


def _same_contact(first: CsatContact, second: CsatContact) -> bool:
    return all(
        (
            first.id == second.id,
            first.external_reference == second.external_reference,
            first.source == second.source,
            first.collaborator_id == second.collaborator_id,
            first.external_operator_identity == second.external_operator_identity,
            first.occurred_on == second.occurred_on,
            first.source_channel == second.source_channel,
            first.score == second.score,
            first.source_context == second.source_context,
        )
    )


def _validate_text(value: str, field_name: str, maximum: int) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if len(value) > maximum:
        raise ValueError(f"{field_name} must not exceed {maximum} characters")
