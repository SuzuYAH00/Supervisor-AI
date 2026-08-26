from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import Engine, bindparam, text

from supervisor_ai.infrastructure.external.mk.contracts import (
    MAX_MK_PAGE_SIZE,
    MkAttendance,
    MkDialogOperatorLink,
    MkDialogSession,
    MkUser,
)

_ATTENDANCE_PAGE = text(
    """
    SELECT
        codatendimento AS attendance_id,
        protocolo AS protocol,
        cliente_cadastrado AS customer_id,
        dt_abertura AS opened_date,
        hr_abertura AS opened_time,
        dh_fim AS closed_at,
        operador_abertura AS opening_operator,
        operador_encerramento AS closing_operator,
        cd_processo AS process_id,
        cd_subprocesso AS subprocess_id,
        classificacao_atendimento AS opening_classification_id,
        classificacao_encerramento AS closing_classification_id,
        como_foi_contato AS origin_id,
        situacao AS status,
        finalizado AS finalized,
        cd_dialogo AS dialog_session_id
    FROM public.mk_atendimento
    WHERE (:after_id IS NULL OR codatendimento > :after_id)
      AND (:opened_from IS NULL OR dt_abertura >= :opened_from)
      AND (:opened_through IS NULL OR dt_abertura <= :opened_through)
    ORDER BY codatendimento ASC
    LIMIT :page_size
    """
)

_ATTENDANCES_BY_ID = text(
    """
    SELECT
        codatendimento AS attendance_id,
        protocolo AS protocol,
        cliente_cadastrado AS customer_id,
        dt_abertura AS opened_date,
        hr_abertura AS opened_time,
        dh_fim AS closed_at,
        operador_abertura AS opening_operator,
        operador_encerramento AS closing_operator,
        cd_processo AS process_id,
        cd_subprocesso AS subprocess_id,
        classificacao_atendimento AS opening_classification_id,
        classificacao_encerramento AS closing_classification_id,
        como_foi_contato AS origin_id,
        situacao AS status,
        finalizado AS finalized,
        cd_dialogo AS dialog_session_id
    FROM public.mk_atendimento
    WHERE codatendimento IN :attendance_ids
    ORDER BY codatendimento ASC
    """
).bindparams(bindparam("attendance_ids", expanding=True))

_DIALOG_PAGE = text(
    """
    SELECT
        cod_dialogosessao AS dialog_session_id,
        protocolo AS protocol,
        nota AS score,
        dh_criacao AS created_at,
        dh_inicio_atendimento AS human_service_started_at,
        dh_encerramento AS closed_at,
        dh_entrada_fila_ate AS entered_queue_at,
        cdsetor AS sector_id,
        codigo_integracao AS integration_code,
        tipo AS channel_type,
        cdpessoa AS person_id
    FROM public.mk_dialogo_sessao
    WHERE (:after_id IS NULL OR cod_dialogosessao > :after_id)
      AND (:created_from IS NULL OR dh_criacao >= :created_from)
      AND (:created_through IS NULL OR dh_criacao <= :created_through)
    ORDER BY cod_dialogosessao ASC
    LIMIT :page_size
    """
)

_DIALOG_OPERATOR_LINKS = text(
    """
    SELECT
        cod_dialogo_sessao_operador AS link_id,
        coddialogosessao AS dialog_session_id,
        usr_codigo AS user_id,
        dh_ingresso AS joined_at,
        dh_saida AS left_at
    FROM public.mk_dialogo_sessao_operador
    WHERE coddialogosessao IN :dialog_session_ids
    ORDER BY coddialogosessao ASC, cod_dialogo_sessao_operador ASC
    """
).bindparams(bindparam("dialog_session_ids", expanding=True))

_USER_PAGE = text(
    """
    SELECT usr_codigo AS user_id, usr_login AS login, usr_nome AS name
    FROM public.fr_usuario
    WHERE (:after_id IS NULL OR usr_codigo > :after_id)
    ORDER BY usr_codigo ASC
    LIMIT :page_size
    """
)

_USERS_BY_ID = text(
    """
    SELECT usr_codigo AS user_id, usr_login AS login, usr_nome AS name
    FROM public.fr_usuario
    WHERE usr_codigo IN :user_ids
    ORDER BY usr_codigo ASC
    """
).bindparams(bindparam("user_ids", expanding=True))


@dataclass(frozen=True, slots=True)
class MkQueryRepositories:
    attendances: MkAttendanceRepository
    dialog_sessions: MkDialogSessionRepository
    users: MkUserRepository

    @classmethod
    def from_engine(cls, engine: Engine) -> MkQueryRepositories:
        return cls(
            MkAttendanceRepository(engine),
            MkDialogSessionRepository(engine),
            MkUserRepository(engine),
        )


class MkAttendanceRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_page(
        self,
        *,
        after_id: int | None = None,
        page_size: int = 100,
        opened_from: date | None = None,
        opened_through: date | None = None,
    ) -> tuple[MkAttendance, ...]:
        _validate_page(after_id, page_size)
        _validate_period(opened_from, opened_through)
        with self._engine.connect() as connection:
            rows = connection.execute(
                _ATTENDANCE_PAGE,
                {
                    "after_id": after_id,
                    "page_size": page_size,
                    "opened_from": opened_from,
                    "opened_through": opened_through,
                },
            ).mappings()
            return tuple(_attendance(row) for row in rows)

    def get_by_ids(self, attendance_ids: tuple[int, ...]) -> tuple[MkAttendance, ...]:
        _validate_ids(attendance_ids, "attendance_ids")
        if len(attendance_ids) > MAX_MK_PAGE_SIZE:
            raise ValueError(f"attendance_ids must not exceed {MAX_MK_PAGE_SIZE} items")
        if not attendance_ids:
            return ()
        with self._engine.connect() as connection:
            rows = connection.execute(
                _ATTENDANCES_BY_ID,
                {"attendance_ids": attendance_ids},
            ).mappings()
            return tuple(_attendance(row) for row in rows)


class MkDialogSessionRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_page(
        self,
        *,
        after_id: int | None = None,
        page_size: int = 100,
        created_from: datetime | None = None,
        created_through: datetime | None = None,
    ) -> tuple[MkDialogSession, ...]:
        _validate_page(after_id, page_size)
        _validate_period(created_from, created_through)
        _validate_naive(created_from, "created_from")
        _validate_naive(created_through, "created_through")
        with self._engine.connect() as connection:
            rows = connection.execute(
                _DIALOG_PAGE,
                {
                    "after_id": after_id,
                    "page_size": page_size,
                    "created_from": created_from,
                    "created_through": created_through,
                },
            ).mappings()
            return tuple(_dialog(row) for row in rows)

    def list_operator_links(
        self, dialog_session_ids: tuple[int, ...]
    ) -> tuple[MkDialogOperatorLink, ...]:
        _validate_ids(dialog_session_ids, "dialog_session_ids")
        if not dialog_session_ids:
            return ()
        with self._engine.connect() as connection:
            rows = connection.execute(
                _DIALOG_OPERATOR_LINKS,
                {"dialog_session_ids": dialog_session_ids},
            ).mappings()
            return tuple(_dialog_operator(row) for row in rows)


class MkUserRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_page(
        self, *, after_id: int | None = None, page_size: int = 100
    ) -> tuple[MkUser, ...]:
        _validate_page(after_id, page_size)
        with self._engine.connect() as connection:
            rows = connection.execute(
                _USER_PAGE,
                {"after_id": after_id, "page_size": page_size},
            ).mappings()
            return tuple(_user(row) for row in rows)

    def get_by_ids(self, user_ids: tuple[int, ...]) -> tuple[MkUser, ...]:
        _validate_ids(user_ids, "user_ids")
        if not user_ids:
            return ()
        with self._engine.connect() as connection:
            rows = connection.execute(_USERS_BY_ID, {"user_ids": user_ids}).mappings()
            return tuple(_user(row) for row in rows)


def _attendance(row) -> MkAttendance:
    return MkAttendance(
        attendance_id=row["attendance_id"],
        protocol=row["protocol"],
        customer_id=row["customer_id"],
        opened_at=_combine_timestamp(row["opened_date"], row["opened_time"]),
        closed_at=row["closed_at"],
        opening_operator=row["opening_operator"],
        closing_operator=row["closing_operator"],
        process_id=row["process_id"],
        subprocess_id=row["subprocess_id"],
        opening_classification_id=row["opening_classification_id"],
        closing_classification_id=row["closing_classification_id"],
        origin_id=row["origin_id"],
        status=None if row["status"] is None else str(row["status"]),
        finalized=None if row["finalized"] is None else str(row["finalized"]),
        dialog_session_id=row["dialog_session_id"],
    )


def _dialog(row) -> MkDialogSession:
    return MkDialogSession(
        dialog_session_id=row["dialog_session_id"],
        protocol=row["protocol"],
        score=row["score"],
        created_at=row["created_at"],
        human_service_started_at=row["human_service_started_at"],
        closed_at=row["closed_at"],
        entered_queue_at=row["entered_queue_at"],
        sector_id=row["sector_id"],
        integration_code=row["integration_code"],
        channel_type=row["channel_type"],
        person_id=row["person_id"],
    )


def _dialog_operator(row) -> MkDialogOperatorLink:
    return MkDialogOperatorLink(
        link_id=row["link_id"],
        dialog_session_id=row["dialog_session_id"],
        user_id=row["user_id"],
        joined_at=row["joined_at"],
        left_at=row["left_at"],
    )


def _user(row) -> MkUser:
    return MkUser(row["user_id"], row["login"], row["name"])


def _combine_timestamp(value: date | None, raw_time: str | None) -> datetime | None:
    if value is None or raw_time is None or not raw_time.strip():
        return None
    return datetime.combine(value, time.fromisoformat(raw_time.strip()))


def _validate_page(after_id: int | None, page_size: int) -> None:
    if after_id is not None and after_id < 0:
        raise ValueError("after_id must not be negative")
    if not 1 <= page_size <= MAX_MK_PAGE_SIZE:
        raise ValueError(f"page_size must be between 1 and {MAX_MK_PAGE_SIZE}")


def _validate_period(start, end) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("period start must not be after period end")


def _validate_naive(value: datetime | None, name: str) -> None:
    if value is not None and value.tzinfo is not None:
        raise ValueError(f"{name} must be a naive MK source timestamp")


def _validate_ids(values: tuple[int, ...], name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{name} must not contain duplicates")
    if any(value <= 0 for value in values):
        raise ValueError(f"{name} must contain positive identifiers")
