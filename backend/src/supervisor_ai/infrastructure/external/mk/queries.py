from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Engine, bindparam, text

from supervisor_ai.infrastructure.external.mk.contracts import (
    MAX_MK_PAGE_SIZE,
    MkAttendance,
    MkAttendanceCatalogSnapshot,
    MkClassificationCatalogEntry,
    MkContract,
    MkContractOperation,
    MkContractPlanChange,
    MkDialogOperatorLink,
    MkDialogSession,
    MkOriginCatalogEntry,
    MkPlan,
    MkProcessCatalogEntry,
    MkSubprocessCatalogEntry,
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

_PROCESS_CATALOG = text(
    """
    SELECT codprocesso AS external_id, nome_processo AS label, inativo
      FROM public.mk_ate_processos
     ORDER BY codprocesso
    """
)
_SUBPROCESS_CATALOG = text(
    """
    SELECT codsubprocesso AS external_id, cd_processo AS process_external_id,
           nome_subprocesso AS label, inativo
      FROM public.mk_ate_subprocessos
     ORDER BY codsubprocesso
    """
)
_CLASSIFICATION_CATALOG = text(
    """
    SELECT codatclass AS external_id, descricao AS label, encerramento, inativar
      FROM public.mk_atendimento_classificacao
     ORDER BY codatclass
    """
)
_ORIGIN_CATALOG = text(
    """
    SELECT cd_orig_cont AS external_id, origem_contato AS label
      FROM public.mk_origem_contato
     ORDER BY cd_orig_cont
    """
)

_CONTRACT_PAGE = text(
    """
    SELECT codcontrato AS contract_id, cliente AS customer_id,
           plano_acesso AS current_plan_id, cancelado, suspenso,
           adesao AS joined_on,
           COALESCE(data_hora_ativacao, dt_ativacao::timestamp) AS activated_at
      FROM public.mk_contratos
     WHERE (:after_id IS NULL OR codcontrato > :after_id)
     ORDER BY codcontrato ASC
     LIMIT :page_size
    """
)
_PLAN_PAGE = text(
    """
    SELECT codplano AS plan_id, descricao, vlr_mensalidade,
           vlr_velocidade AS download_speed,
           vlr_velocidade_up AS upload_speed, velocidades_formatadas
      FROM public.mk_planos_acesso
     WHERE (:after_id IS NULL OR codplano > :after_id)
     ORDER BY codplano ASC
     LIMIT :page_size
    """
)
_CONTRACT_OPERATION_CATALOG = text(
    """
    SELECT codcontratooperacao AS operation_code,
           descricao_operacao AS description
      FROM public.mk_contratos_operacoes
     ORDER BY codcontratooperacao
    """
)
_PLAN_CHANGE_PAGE = text(
    """
    WITH unique_users AS (
        SELECT lower(trim(usr_login)) AS normalized_login,
               min(usr_codigo) AS user_id
          FROM public.fr_usuario
         GROUP BY lower(trim(usr_login))
        HAVING count(*) = 1
    )
    SELECT h.codcontratohist AS plan_change_id,
           h.cd_contrato AS contract_id,
           h.cd_operacao AS operation_code,
           h.cd_plano_velho AS old_plan_id,
           h.cd_plano_novo AS new_plan_id,
           h.dt_hr AS changed_at,
           h.operador AS changed_by_login,
           u.user_id AS changed_by_user_id,
           h.vlr AS value_delta,
           h.tx_extra AS extra_context
      FROM public.mk_contratos_historicos h
      LEFT JOIN unique_users u
        ON u.normalized_login = lower(trim(h.operador))
     WHERE (:after_id IS NULL OR h.codcontratohist > :after_id)
     ORDER BY h.codcontratohist ASC
     LIMIT :page_size
    """
)


@dataclass(frozen=True, slots=True)
class MkQueryRepositories:
    attendances: MkAttendanceRepository
    dialog_sessions: MkDialogSessionRepository
    users: MkUserRepository
    attendance_catalogs: MkAttendanceCatalogRepository
    contracts: MkContractRepository
    plans: MkPlanRepository
    contract_plan_changes: MkContractPlanChangeRepository
    contract_operations: MkContractOperationRepository

    @classmethod
    def from_engine(cls, engine: Engine) -> MkQueryRepositories:
        return cls(
            MkAttendanceRepository(engine),
            MkDialogSessionRepository(engine),
            MkUserRepository(engine),
            MkAttendanceCatalogRepository(engine),
            MkContractRepository(engine),
            MkPlanRepository(engine),
            MkContractPlanChangeRepository(engine),
            MkContractOperationRepository(engine),
        )


class MkContractRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_page(
        self, *, after_id: int | None = None, page_size: int = 100
    ) -> tuple[MkContract, ...]:
        _validate_page(after_id, page_size)
        with self._engine.connect() as connection:
            rows = connection.execute(
                _CONTRACT_PAGE, {"after_id": after_id, "page_size": page_size}
            ).mappings()
            return tuple(_contract(row) for row in rows)


class MkPlanRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_page(
        self, *, after_id: int | None = None, page_size: int = 100
    ) -> tuple[MkPlan, ...]:
        _validate_page(after_id, page_size)
        with self._engine.connect() as connection:
            rows = connection.execute(
                _PLAN_PAGE, {"after_id": after_id, "page_size": page_size}
            ).mappings()
            return tuple(_plan(row) for row in rows)


class MkContractPlanChangeRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_page(
        self, *, after_id: int | None = None, page_size: int = 100
    ) -> tuple[MkContractPlanChange, ...]:
        _validate_page(after_id, page_size)
        with self._engine.connect() as connection:
            rows = connection.execute(
                _PLAN_CHANGE_PAGE,
                {"after_id": after_id, "page_size": page_size},
            ).mappings()
            return tuple(_plan_change(row) for row in rows)


class MkContractOperationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self) -> tuple[MkContractOperation, ...]:
        with self._engine.connect() as connection:
            return tuple(
                MkContractOperation(row["operation_code"], row["description"])
                for row in connection.execute(_CONTRACT_OPERATION_CATALOG).mappings()
            )


class MkAttendanceCatalogRepository:
    """Carrega os quatro catálogos pequenos sem N+1."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self) -> MkAttendanceCatalogSnapshot:
        with self._engine.connect() as connection:
            processes = tuple(
                MkProcessCatalogEntry(
                    row["external_id"],
                    row["label"],
                    _optional_mk_boolean(row["inativo"]),
                )
                for row in connection.execute(_PROCESS_CATALOG).mappings()
                if row["label"]
            )
            subprocesses = tuple(
                MkSubprocessCatalogEntry(
                    row["external_id"],
                    row["process_external_id"],
                    row["label"],
                    _optional_mk_boolean(row["inativo"]),
                )
                for row in connection.execute(_SUBPROCESS_CATALOG).mappings()
                if row["label"]
            )
            classifications = tuple(
                MkClassificationCatalogEntry(
                    row["external_id"],
                    row["label"],
                    _optional_mk_boolean(row["encerramento"]),
                    _optional_mk_boolean(row["inativar"]),
                )
                for row in connection.execute(_CLASSIFICATION_CATALOG).mappings()
                if row["label"]
            )
            origins = tuple(
                MkOriginCatalogEntry(row["external_id"], row["label"])
                for row in connection.execute(_ORIGIN_CATALOG).mappings()
                if row["label"]
            )
        return MkAttendanceCatalogSnapshot(
            processes, subprocesses, classifications, origins
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


def _contract(row) -> MkContract:
    return MkContract(
        contract_id=row["contract_id"],
        customer_id=row["customer_id"],
        current_plan_id=row["current_plan_id"],
        cancelled=_optional_text(row["cancelado"]),
        suspended=_optional_text(row["suspenso"]),
        joined_on=row["joined_on"],
        activated_at=row["activated_at"],
    )


def _plan(row) -> MkPlan:
    return MkPlan(
        plan_id=row["plan_id"],
        description=row["descricao"],
        monthly_value=_optional_decimal(row["vlr_mensalidade"]),
        download_speed=row["download_speed"],
        upload_speed=row["upload_speed"],
        formatted_speeds=row["velocidades_formatadas"],
    )


def _plan_change(row) -> MkContractPlanChange:
    return MkContractPlanChange(
        plan_change_id=row["plan_change_id"],
        contract_id=row["contract_id"],
        operation_code=row["operation_code"],
        old_plan_id=row["old_plan_id"],
        new_plan_id=row["new_plan_id"],
        changed_at=row["changed_at"],
        changed_by_login=row["changed_by_login"],
        changed_by_user_id=row["changed_by_user_id"],
        value_delta=_optional_decimal(row["value_delta"]),
        extra_context=row["extra_context"],
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


def _optional_mk_boolean(value: str | None) -> bool | None:
    if value is None:
        return None
    return _mk_boolean(value)


def _optional_text(value: str | None) -> str | None:
    return None if value is None else value.strip()


def _optional_decimal(value: object | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _mk_boolean(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"s", "sim", "1", "true"}:
        return True
    if normalized in {"n", "nao", "não", "0", "false"}:
        return False
    raise ValueError("unsupported MK boolean value")
