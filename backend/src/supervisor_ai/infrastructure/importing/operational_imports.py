from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from supervisor_ai.application.use_cases import (
    ImportDailyWorkStatusesCommand,
    ImportNpxFactsCommand,
    ImportWorkSchedulesCommand,
    NpxCoverageDeclaration,
)
from supervisor_ai.infrastructure.importing.csat_source_xlsx import (
    MkCsatXlsxImportService,
    NpxCsatXlsxImportService,
)
from supervisor_ai.infrastructure.importing.employee_occurrence_xlsx import (
    EmployeeOccurrenceXlsxImportService,
)
from supervisor_ai.infrastructure.importing.npx_workforce_xlsx import (
    parse_npx_pauses_xlsx,
    parse_npx_work_sessions_xlsx,
)
from supervisor_ai.infrastructure.importing.workforce_schedule_xlsx import (
    parse_work_schedules_xlsx,
    parse_workforce_schedule_xlsx,
)


class OperationalImportType(StrEnum):
    WORKFORCE_SCHEDULE = "workforce_schedule"
    CSAT_CHAT_MK = "csat_chat_mk"
    CSAT_PHONE_NPX = "csat_phone_npx"
    RECURRENCE_MK = "recurrence_mk"
    NPX_WORK_SESSIONS = "npx_work_sessions"
    NPX_PAUSES = "npx_pauses"
    EMPLOYEE_OCCURRENCES = "employee_occurrences"


@dataclass(frozen=True, slots=True)
class OperationalImportDefinition:
    import_type: OperationalImportType
    label: str
    source: str
    ready: bool
    requires_competence: bool
    accepted_extensions: tuple[str, ...]
    not_ready_reason: str | None = None


@dataclass(frozen=True, slots=True)
class OperationalImportIssue:
    code: str
    message: str
    row: int | None = None
    sheet: str | None = None
    field: str | None = None
    raw_value: str | None = None
    external_identity: str | None = None


@dataclass(frozen=True, slots=True)
class OperationalImportCoverage:
    dataset: str
    source: str
    covered_through: date


@dataclass(frozen=True, slots=True)
class OperationalImportResult:
    import_type: OperationalImportType
    source: str
    filename: str
    competence_month: date | None
    total_records: int
    accepted_records: int
    duplicate_records: int
    rejected_records: int
    conflict_records: int
    issues: tuple[OperationalImportIssue, ...] = ()
    coverages: tuple[OperationalImportCoverage, ...] = ()
    warnings: tuple[str, ...] = ()
    processing_run_id: str | None = None


CATALOG = (
    OperationalImportDefinition(
        OperationalImportType.WORKFORCE_SCHEDULE,
        "Escala",
        "attendance_sheet",
        True,
        True,
        (".xlsx",),
    ),
    OperationalImportDefinition(
        OperationalImportType.CSAT_CHAT_MK,
        "CSAT Chat / MK",
        "mk",
        True,
        False,
        (".xlsx",),
    ),
    OperationalImportDefinition(
        OperationalImportType.CSAT_PHONE_NPX,
        "CSAT Ligação / NPX",
        "npx",
        True,
        False,
        (".xlsx",),
    ),
    OperationalImportDefinition(
        OperationalImportType.RECURRENCE_MK,
        "Reincidência / MK",
        "mk",
        False,
        True,
        (".xlsx",),
        "O relatório MK real ainda não possui parser XLSX canônico.",
    ),
    OperationalImportDefinition(
        OperationalImportType.NPX_WORK_SESSIONS,
        "NPX Pontos",
        "npx",
        True,
        True,
        (".xlsx",),
    ),
    OperationalImportDefinition(
        OperationalImportType.NPX_PAUSES, "NPX Pausas", "npx", True, True, (".xlsx",)
    ),
    OperationalImportDefinition(
        OperationalImportType.EMPLOYEE_OCCURRENCES,
        "Ocorrências / Google Forms",
        "google_forms_employee_occurrences",
        True,
        False,
        (".xlsx",),
    ),
)


class CommandExecutor(Protocol):
    def execute(self, command): ...


class OperationalImportService:
    def __init__(
        self,
        daily_statuses: CommandExecutor,
        work_schedules: CommandExecutor,
        mk_csat: MkCsatXlsxImportService,
        npx_csat: NpxCsatXlsxImportService,
        npx_facts: CommandExecutor,
        employee_occurrences: EmployeeOccurrenceXlsxImportService,
    ) -> None:
        self._daily_statuses = daily_statuses
        self._work_schedules = work_schedules
        self._mk_csat = mk_csat
        self._npx_csat = npx_csat
        self._npx_facts = npx_facts
        self._employee_occurrences = employee_occurrences

    @staticmethod
    def catalog() -> tuple[OperationalImportDefinition, ...]:
        return CATALOG

    def import_file(
        self,
        import_type: OperationalImportType,
        filename: str,
        content: bytes,
        competence_month: date | None,
    ) -> OperationalImportResult:
        definition = next(item for item in CATALOG if item.import_type is import_type)
        if not definition.ready:
            raise NotImplementedError(definition.not_ready_reason)
        if definition.requires_competence and competence_month is None:
            raise ValueError("competence_month is required for this import type")
        reference = f"{filename}:{sha256(content).hexdigest()}"
        if import_type is OperationalImportType.WORKFORCE_SCHEDULE:
            statuses = parse_workforce_schedule_xlsx(content)
            standards, daily = parse_work_schedules_xlsx(content)
            status_result = self._daily_statuses.execute(
                ImportDailyWorkStatusesCommand(statuses)
            )
            schedule_result = self._work_schedules.execute(
                ImportWorkSchedulesCommand(
                    standards, daily, _month_end(competence_month), reference
                )
            )
            total = len(statuses) + len(standards) + len(daily)
            created = (
                status_result.created_count
                + schedule_result.created_standards
                + schedule_result.created_daily_schedules
            )
            duplicates = (
                status_result.already_existing_count + schedule_result.idempotent_items
            )
            return OperationalImportResult(
                import_type,
                definition.source,
                filename,
                competence_month,
                total,
                created,
                duplicates,
                0,
                0,
                coverages=(
                    OperationalImportCoverage(
                        "planned_work_schedules",
                        definition.source,
                        _month_end(competence_month),
                    ),
                ),
            )
        if import_type in {
            OperationalImportType.CSAT_CHAT_MK,
            OperationalImportType.CSAT_PHONE_NPX,
        }:
            result = (
                self._mk_csat
                if import_type is OperationalImportType.CSAT_CHAT_MK
                else self._npx_csat
            ).import_xlsx(content)
            return OperationalImportResult(
                import_type,
                definition.source,
                filename,
                competence_month,
                result.received_count,
                result.created_count,
                result.already_existing_count,
                0,
                0,
            )
        if import_type in {
            OperationalImportType.NPX_WORK_SESSIONS,
            OperationalImportType.NPX_PAUSES,
        }:
            coverage = NpxCoverageDeclaration(_month_end(competence_month), reference)
            if import_type is OperationalImportType.NPX_WORK_SESSIONS:
                inputs = parse_npx_work_sessions_xlsx(
                    content, extract_reference=reference
                )
                result = self._npx_facts.execute(
                    ImportNpxFactsCommand(
                        work_sessions=inputs, work_session_coverage=coverage
                    )
                )
                created = result.imported_work_sessions
                dataset = "npx_work_sessions"
            else:
                inputs = parse_npx_pauses_xlsx(content, extract_reference=reference)
                result = self._npx_facts.execute(
                    ImportNpxFactsCommand(pauses=inputs, pause_coverage=coverage)
                )
                created = result.imported_pauses
                dataset = "npx_pauses"
            issues = tuple(
                OperationalImportIssue(
                    item.code,
                    _issue_message(item.code),
                    row=item.source_row,
                    raw_value=item.invalid_value,
                    external_identity=item.external_identity,
                )
                for item in result.issues
            )
            return OperationalImportResult(
                import_type,
                definition.source,
                filename,
                competence_month,
                len(inputs),
                created,
                result.idempotent_rows,
                result.rejected_rows,
                result.conflict_rows,
                issues,
                (
                    OperationalImportCoverage(
                        dataset, definition.source, coverage.covered_through
                    ),
                ),
            )
        result = self._employee_occurrences.import_xlsx(content)
        issues = tuple(
            OperationalImportIssue(
                item.code,
                _issue_message(item.code),
                row=item.row_number,
                raw_value=item.invalid_value,
                external_identity=item.external_identity,
            )
            for item in result.issues
        )
        return OperationalImportResult(
            import_type,
            definition.source,
            filename,
            competence_month,
            result.total_data_rows,
            result.imported_rows,
            result.idempotent_rows,
            result.rejected_rows,
            result.conflict_rows,
            issues,
        )


def _month_end(month: date | None) -> date:
    if month is None or month.day != 1:
        raise ValueError("competence_month must be the first day of a month")
    following = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    return date.fromordinal(following.toordinal() - 1)


def _issue_message(code: str) -> str:
    return {
        "unknown_collaborator_alias": (
            "A identidade externa não possui alias cadastrado."
        ),
        "conflicting_work_session": "A sessão diverge de um fato já importado.",
        "conflicting_pause": "A pausa diverge de um fato já importado.",
        "conflicting_occurrence": "A ocorrência diverge de um fato já importado.",
        "invalid_occurrence_date": (
            "A data da ocorrência não usa DD/MM/AA ou DD/MM/AAAA."
        ),
        "invalid_submitted_at": "O carimbo de envio é inválido.",
        "invalid_required_field": "Um campo obrigatório não foi preenchido.",
    }.get(code, "O registro não pôde ser importado.")
