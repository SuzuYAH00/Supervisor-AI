from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

MAX_MK_PAGE_SIZE = 1000


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


class MkAttendanceQuery(Protocol):
    def list_page(
        self,
        *,
        after_id: int | None = None,
        page_size: int = 100,
        opened_from: date | None = None,
        opened_through: date | None = None,
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
