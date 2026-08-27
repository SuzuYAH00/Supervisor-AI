from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from time import monotonic
from zoneinfo import ZoneInfo

from supervisor_ai.application.mk_operational import (
    MK_ATTENDANCE_FACT_SOURCE,
    MK_EXTERNAL_IDENTITY_SOURCE,
    MkAttendanceMirror,
)
from supervisor_ai.application.persistence import AttendanceFact
from supervisor_ai.application.ports import Clock, UnitOfWorkFactory
from supervisor_ai.infrastructure.external.mk.contracts import (
    MkAttendanceCatalogSnapshot,
)
from supervisor_ai.rules_engine import (
    ELIGIBLE_CLOSING_CLASSIFICATIONS,
    ELIGIBLE_OPENING_CLASSIFICATIONS,
    ELIGIBLE_PROCESS,
    ClassificationIdentity,
)

_FORTALEZA = ZoneInfo("America/Fortaleza")
DEFAULT_PROJECTION_BATCH_SIZE = 500
MAX_PROJECTION_BATCH_SIZE = 1000


class MkAttendanceProjectionStatus(StrEnum):
    PROJECTED = "projected"
    UNCHANGED = "unchanged"
    NOT_READY_FOR_PROJECTION = "not_ready_for_projection"
    UNRESOLVED_OPERATOR = "unresolved_operator"
    UNRESOLVED_CATALOG = "unresolved_catalog"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class MkAttendanceCatalog:
    processes: Mapping[str, ClassificationIdentity]
    opening_classifications: Mapping[str, ClassificationIdentity]
    closing_classifications: Mapping[str, ClassificationIdentity]
    channels: Mapping[str, str]


_CATALOG_LABEL_ALIASES = {
    "008 - Problemas IPTV": ClassificationIdentity("008", "Problemas no IPTV"),
    "012 - Entrega/Config. Roteador": ClassificationIdentity(
        "012", "Entrga/Config. Roteador"
    ),
    "030 - Alteração de Plano": ClassificationIdentity("030", "Alteração de plano"),
}


def build_recurrence_catalog(
    snapshot: MkAttendanceCatalogSnapshot,
) -> MkAttendanceCatalog:
    """Relaciona PKs MK a identidades normativas sem extrair códigos do texto."""
    process_label = _catalog_label(ELIGIBLE_PROCESS)
    processes = {
        str(item.external_id): (
            ELIGIBLE_PROCESS
            if item.label == process_label
            else ClassificationIdentity(None, item.label)
        )
        for item in snapshot.processes
    }
    opening_by_label = {
        _catalog_label(identity): identity
        for identity in ELIGIBLE_OPENING_CLASSIFICATIONS
    }
    closing_by_label = {
        _catalog_label(identity): identity
        for identity in ELIGIBLE_CLOSING_CLASSIFICATIONS
    }
    opening: dict[str, ClassificationIdentity] = {}
    closing: dict[str, ClassificationIdentity] = {}
    for item in snapshot.classifications:
        identity = ClassificationIdentity(None, item.label)
        if item.closing is False:
            identity = opening_by_label.get(
                item.label, _CATALOG_LABEL_ALIASES.get(item.label, identity)
            )
            opening[str(item.external_id)] = identity
        elif item.closing is True:
            identity = closing_by_label.get(item.label, identity)
            closing[str(item.external_id)] = identity
    return MkAttendanceCatalog(
        processes=processes,
        opening_classifications=opening,
        closing_classifications=closing,
        channels={str(item.external_id): item.label for item in snapshot.origins},
    )


@dataclass(frozen=True, slots=True)
class ProjectMkAttendancesCommand:
    opened_from: date
    opened_through: date
    batch_size: int = DEFAULT_PROJECTION_BATCH_SIZE

    def __post_init__(self) -> None:
        if self.opened_from > self.opened_through:
            raise ValueError("opened_from must not be after opened_through")
        if not 1 <= self.batch_size <= MAX_PROJECTION_BATCH_SIZE:
            raise ValueError(
                f"batch_size must be between 1 and {MAX_PROJECTION_BATCH_SIZE}"
            )


@dataclass(frozen=True, slots=True)
class MkAttendanceProjectionItem:
    external_id: str
    protocol: str | None
    status: MkAttendanceProjectionStatus
    attendance_fact_id: str | None = None
    missing_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectMkAttendancesResult:
    items: tuple[MkAttendanceProjectionItem, ...]
    duration_seconds: float

    @property
    def candidates(self) -> int:
        return len(self.items)

    def count(self, status: MkAttendanceProjectionStatus) -> int:
        return sum(item.status is status for item in self.items)


class ProjectMkAttendancesUseCase:
    """Projeta apenas mirrors finais com catálogos e operador resolvidos."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        catalog: MkAttendanceCatalog,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._catalog = catalog

    def execute(
        self, command: ProjectMkAttendancesCommand
    ) -> ProjectMkAttendancesResult:
        started = monotonic()
        opened_from, opened_before = _utc_period(command)
        clock_value = self._clock()
        if clock_value.tzinfo is None or clock_value.utcoffset() is None:
            raise ValueError("projection clock must return a timezone-aware datetime")
        created_at = clock_value.astimezone(UTC)
        items: list[MkAttendanceProjectionItem] = []
        after_external_id: str | None = None

        while True:
            with self._unit_of_work_factory() as unit_of_work:
                mirrors = unit_of_work.mk_attendances.list_projection_candidates(
                    opened_from=opened_from,
                    opened_before=opened_before,
                    after_external_id=after_external_id,
                    limit=command.batch_size,
                )
                if not mirrors:
                    break
                operator_ids = tuple(
                    dict.fromkeys(
                        item.closing_operator_external_id
                        for item in mirrors
                        if item.closing_operator_external_id is not None
                    )
                )
                identities = (
                    unit_of_work.collaborator_external_identities
                    .get_by_source_identities(
                        source=MK_EXTERNAL_IDENTITY_SOURCE,
                        external_identities=operator_ids,
                    )
                )
                collaborators = {
                    identity.external_identity: identity.collaborator_id
                    for identity in identities
                }
                for mirror in mirrors:
                    result, fact = self._map(mirror, collaborators, created_at)
                    if fact is not None:
                        existing = unit_of_work.attendances.get_by_source_reference(
                            source=fact.source,
                            external_reference=fact.external_reference,
                        )
                        if existing is None:
                            unit_of_work.attendances.add(fact)
                            result = MkAttendanceProjectionItem(
                                mirror.external_id,
                                mirror.protocol,
                                MkAttendanceProjectionStatus.PROJECTED,
                                fact.id,
                            )
                        elif _same_fact(existing, fact):
                            result = MkAttendanceProjectionItem(
                                mirror.external_id,
                                mirror.protocol,
                                MkAttendanceProjectionStatus.UNCHANGED,
                                existing.id,
                            )
                        else:
                            result = MkAttendanceProjectionItem(
                                mirror.external_id,
                                mirror.protocol,
                                MkAttendanceProjectionStatus.REJECTED,
                                existing.id,
                                ("persisted_fact_conflict",),
                            )
                    items.append(result)
                after_external_id = mirrors[-1].external_id
                unit_of_work.commit()

            if len(mirrors) < command.batch_size:
                break

        return ProjectMkAttendancesResult(tuple(items), monotonic() - started)

    def _map(
        self,
        mirror: MkAttendanceMirror,
        collaborators: Mapping[str, str],
        created_at: datetime,
    ) -> tuple[MkAttendanceProjectionItem, AttendanceFact | None]:
        missing_fact = tuple(
            name
            for name, value in (
                ("protocol", mirror.protocol),
                ("customer_external_id", mirror.customer_external_id),
                ("closed_at", mirror.closed_at),
                (
                    "responsible_operator_external_id",
                    mirror.closing_operator_external_id,
                ),
                ("process_external_id", mirror.process_external_id),
                (
                    "opening_classification_external_id",
                    mirror.opening_classification_external_id,
                ),
                (
                    "closing_classification_external_id",
                    mirror.closing_classification_external_id,
                ),
                ("origin_external_id", mirror.origin_external_id),
            )
            if value is None
        )
        if mirror.is_finalized is not True or missing_fact:
            return (
                MkAttendanceProjectionItem(
                    mirror.external_id,
                    mirror.protocol,
                    MkAttendanceProjectionStatus.NOT_READY_FOR_PROJECTION,
                    missing_fields=missing_fact or ("is_finalized",),
                ),
                None,
            )
        operator_external_id = mirror.closing_operator_external_id
        operator = collaborators.get(operator_external_id)
        if operator is None:
            return (
                MkAttendanceProjectionItem(
                    mirror.external_id,
                    mirror.protocol,
                    MkAttendanceProjectionStatus.UNRESOLVED_OPERATOR,
                    missing_fields=("responsible_operator_external_id",),
                ),
                None,
            )
        process = self._catalog.processes.get(mirror.process_external_id)
        opening = self._catalog.opening_classifications.get(
            mirror.opening_classification_external_id
        )
        closing = self._catalog.closing_classifications.get(
            mirror.closing_classification_external_id
        )
        channel = self._catalog.channels.get(mirror.origin_external_id)
        unresolved = tuple(
            name
            for name, value in (
                ("process_external_id", process),
                ("opening_classification_external_id", opening),
                ("closing_classification_external_id", closing),
                ("origin_external_id", channel),
            )
            if value is None
        )
        if unresolved:
            return (
                MkAttendanceProjectionItem(
                    mirror.external_id,
                    mirror.protocol,
                    MkAttendanceProjectionStatus.UNRESOLVED_CATALOG,
                    missing_fields=unresolved,
                ),
                None,
            )
        assert mirror.customer_external_id is not None
        assert process is not None and opening is not None and closing is not None
        assert channel is not None
        fact = AttendanceFact(
            id=f"mk-attendance:{mirror.external_id}",
            external_reference=mirror.external_id,
            source=MK_ATTENDANCE_FACT_SOURCE,
            customer_code=mirror.customer_external_id,
            operator_id=operator,
            channel=channel,
            occurred_at=mirror.opened_at,
            process=process,
            opening_classification=opening,
            closing_classification=closing,
            created_at=created_at,
        )
        return (
            MkAttendanceProjectionItem(
                mirror.external_id,
                mirror.protocol,
                MkAttendanceProjectionStatus.PROJECTED,
                fact.id,
            ),
            fact,
        )

def _utc_period(command: ProjectMkAttendancesCommand) -> tuple[datetime, datetime]:
    start = datetime.combine(command.opened_from, time.min, tzinfo=_FORTALEZA)
    end = datetime.combine(
        command.opened_through + timedelta(days=1), time.min, tzinfo=_FORTALEZA
    )
    return start.astimezone(UTC), end.astimezone(UTC)


def _catalog_label(identity: ClassificationIdentity) -> str:
    if identity.code is None:
        return identity.description
    return f"{identity.code} - {identity.description}"


def _same_fact(first: AttendanceFact, second: AttendanceFact) -> bool:
    fields = (
        "id",
        "external_reference",
        "source",
        "customer_code",
        "operator_id",
        "channel",
        "occurred_at",
        "process",
        "opening_classification",
        "closing_classification",
    )
    return all(getattr(first, field) == getattr(second, field) for field in fields)
