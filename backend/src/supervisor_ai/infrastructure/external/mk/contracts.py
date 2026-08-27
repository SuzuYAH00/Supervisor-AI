from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

MAX_MK_PAGE_SIZE = 1000
MK_CONTRACT_OPERATION_UPGRADE = 4
MK_CONTRACT_OPERATION_DOWNGRADE = 5


@dataclass(frozen=True, slots=True)
class MkContract:
    contract_id: int
    customer_id: int
    current_plan_id: int
    cancelled: str | None
    suspended: str | None
    joined_on: date | None
    activated_at: datetime | None


@dataclass(frozen=True, slots=True)
class MkPlan:
    plan_id: int
    description: str
    monthly_value: Decimal | None
    download_speed: int | None
    upload_speed: int | None
    formatted_speeds: str | None


@dataclass(frozen=True, slots=True)
class MkContractOperation:
    operation_code: int
    description: str


@dataclass(frozen=True, slots=True)
class MkContractPlanChange:
    plan_change_id: int
    contract_id: int
    operation_code: int
    old_plan_id: int | None
    new_plan_id: int | None
    changed_at: datetime
    changed_by_login: str
    changed_by_user_id: int | None
    value_delta: Decimal | None
    extra_context: str | None


@dataclass(frozen=True, slots=True)
class MkAttendance:
    attendance_id: int
    protocol: str | None
    customer_id: int | None
    opened_at: datetime | None
    closed_at: datetime | None
    opening_operator: str | None
    closing_operator: str | None
    process_id: int | None
    subprocess_id: int | None
    opening_classification_id: int | None
    closing_classification_id: int | None
    origin_id: int | None
    status: str | None
    finalized: str | None
    dialog_session_id: int | None


@dataclass(frozen=True, slots=True)
class MkDialogSession:
    dialog_session_id: int
    protocol: str | None
    score: int | None
    created_at: datetime
    human_service_started_at: datetime | None
    closed_at: datetime | None
    entered_queue_at: datetime | None
    sector_id: int | None
    integration_code: str | None
    channel_type: str | None
    person_id: int | None


@dataclass(frozen=True, slots=True)
class MkDialogOperatorLink:
    link_id: int
    dialog_session_id: int
    user_id: int
    joined_at: datetime | None
    left_at: datetime | None


@dataclass(frozen=True, slots=True)
class MkUser:
    user_id: int
    login: str
    name: str


@dataclass(frozen=True, slots=True)
class MkProcessCatalogEntry:
    external_id: int
    label: str
    inactive: bool | None


@dataclass(frozen=True, slots=True)
class MkSubprocessCatalogEntry:
    external_id: int
    process_external_id: int | None
    label: str
    inactive: bool | None


@dataclass(frozen=True, slots=True)
class MkClassificationCatalogEntry:
    external_id: int
    label: str
    closing: bool | None
    inactive: bool | None


@dataclass(frozen=True, slots=True)
class MkOriginCatalogEntry:
    external_id: int
    label: str


@dataclass(frozen=True, slots=True)
class MkAttendanceCatalogSnapshot:
    processes: tuple[MkProcessCatalogEntry, ...]
    subprocesses: tuple[MkSubprocessCatalogEntry, ...]
    classifications: tuple[MkClassificationCatalogEntry, ...]
    origins: tuple[MkOriginCatalogEntry, ...]


class MkAttendanceQuery(Protocol):
    def list_page(
        self,
        *,
        after_id: int | None = None,
        page_size: int = 100,
        opened_from: date | None = None,
        opened_through: date | None = None,
    ) -> tuple[MkAttendance, ...]: ...

    def get_by_ids(
        self, attendance_ids: tuple[int, ...]
    ) -> tuple[MkAttendance, ...]: ...


class MkDialogSessionQuery(Protocol):
    def list_page(
        self,
        *,
        after_id: int | None = None,
        page_size: int = 100,
        created_from: datetime | None = None,
        created_through: datetime | None = None,
    ) -> tuple[MkDialogSession, ...]: ...

    def list_operator_links(
        self, dialog_session_ids: tuple[int, ...]
    ) -> tuple[MkDialogOperatorLink, ...]: ...


class MkUserQuery(Protocol):
    def list_page(
        self, *, after_id: int | None = None, page_size: int = 100
    ) -> tuple[MkUser, ...]: ...

    def get_by_ids(self, user_ids: tuple[int, ...]) -> tuple[MkUser, ...]: ...


class MkAttendanceCatalogQuery(Protocol):
    def load(self) -> MkAttendanceCatalogSnapshot: ...


class MkContractQuery(Protocol):
    def list_page(
        self, *, after_id: int | None = None, page_size: int = 100
    ) -> tuple[MkContract, ...]: ...


class MkPlanQuery(Protocol):
    def list_page(
        self, *, after_id: int | None = None, page_size: int = 100
    ) -> tuple[MkPlan, ...]: ...


class MkContractPlanChangeQuery(Protocol):
    def list_page(
        self, *, after_id: int | None = None, page_size: int = 100
    ) -> tuple[MkContractPlanChange, ...]: ...


class MkContractOperationQuery(Protocol):
    def load(self) -> tuple[MkContractOperation, ...]: ...
