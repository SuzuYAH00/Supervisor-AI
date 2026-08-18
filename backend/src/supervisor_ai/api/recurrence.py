from datetime import date, datetime
from typing import Annotated, Protocol

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.projections import decimal_string
from supervisor_ai.api.schemas import (
    AttendanceFiltersResponse,
    AttendanceImportResponse,
    AttendanceListResponse,
    AttendanceResponse,
    ClassificationIdentityResponse,
    ErrorResponse,
    RecurrenceCohortResponse,
    RecurrenceOccurrenceResponse,
    RecurrenceOperatorSummaryResponse,
    RecurrenceSummaryResponse,
)
from supervisor_ai.application import (
    AttendanceFactConflict,
    AttendanceFilters,
    IngestionCoverageConflict,
    RecurrenceCohortQuery,
)
from supervisor_ai.application.use_cases import (
    AttendanceCoverageDeclaration,
    GetAttendancesResult,
    GetRecurrenceSummaryResult,
    ImportAttendancesResult,
)
from supervisor_ai.infrastructure.importing import (
    AttendanceCsvStructureError,
    AttendanceCsvValidationError,
)
from supervisor_ai.rules_engine import ClassificationIdentity


class AttendanceCsvImportServiceContract(Protocol):
    def import_csv(
        self,
        content: str,
        *,
        coverage: AttendanceCoverageDeclaration | None = None,
    ) -> ImportAttendancesResult: ...


class AttendanceQueryServiceContract(Protocol):
    def execute(self, query: AttendanceFilters) -> GetAttendancesResult: ...


class RecurrenceSummaryServiceContract(Protocol):
    def execute(
        self, query: RecurrenceCohortQuery
    ) -> GetRecurrenceSummaryResult: ...


def recurrence_router(
    importer: AttendanceCsvImportServiceContract,
    attendance_query: AttendanceQueryServiceContract,
    summary: RecurrenceSummaryServiceContract,
) -> APIRouter:
    router = APIRouter(tags=["recurrence"])

    @router.post(
        "/imports/recurrence/attendances/csv",
        response_model=AttendanceImportResponse,
        responses={
            400: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        summary="Importa fatos de atendimento para cálculo de reincidência",
        description=(
            "Persiste os fatos sem decidir elegibilidade ou reincidência. "
            "Código e descrição formam a identidade das classificações."
        ),
    )
    async def import_attendances_csv(
        file: Annotated[UploadFile, File()],
        coverage_source: Annotated[
            str | None, Form(min_length=1, max_length=100)
        ] = None,
        covered_through: Annotated[date | None, Form()] = None,
        coverage_reference: Annotated[
            str | None, Form(min_length=1, max_length=255)
        ] = None,
    ) -> AttendanceImportResponse | JSONResponse:
        if not file.filename:
            return error_response(
                422, "invalid_attendance_upload", "Attendance CSV filename is required"
            )
        try:
            content_bytes = await file.read()
        except Exception:
            return error_response(
                500,
                "attendance_upload_read_error",
                "Attendance CSV upload could not be read",
            )
        if not content_bytes:
            return error_response(
                422, "empty_attendance_upload", "Attendance CSV file must not be empty"
            )
        try:
            content = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            return error_response(
                422,
                "invalid_attendance_encoding",
                "Attendance CSV file must use UTF-8 encoding",
            )
        coverage_values = (
            coverage_source,
            covered_through,
            coverage_reference,
        )
        if any(value is not None for value in coverage_values) and not all(
            value is not None for value in coverage_values
        ):
            return error_response(
                422,
                "incomplete_ingestion_coverage",
                "Coverage source, date and reference must be provided together",
            )
        coverage = (
            AttendanceCoverageDeclaration(
                source=coverage_source,
                covered_through=covered_through,
                import_reference=coverage_reference,
            )
            if coverage_source is not None
            and covered_through is not None
            and coverage_reference is not None
            else None
        )
        try:
            result = (
                importer.import_csv(content)
                if coverage is None
                else importer.import_csv(content, coverage=coverage)
            )
        except AttendanceCsvStructureError:
            return error_response(
                400,
                "attendance_csv_structure_error",
                "Attendance CSV structure is invalid",
            )
        except AttendanceCsvValidationError:
            return error_response(
                422,
                "invalid_attendance_data",
                "Attendance CSV contains invalid data",
            )
        except AttendanceFactConflict:
            return error_response(
                409,
                "attendance_fact_conflict",
                "Attendance conflicts with persisted facts",
            )
        except IngestionCoverageConflict:
            return error_response(
                409,
                "ingestion_coverage_conflict",
                "Coverage reference conflicts with persisted evidence",
            )
        except Exception:
            return error_response(
                500, "internal_error", "Attendance CSV import could not be completed"
            )
        return AttendanceImportResponse(
            received_count=result.received_count,
            created_count=result.created_count,
            already_existing_count=result.already_existing_count,
            attendance_ids=list(result.attendance_ids),
            declared_covered_through=result.declared_covered_through,
            effective_covered_through=result.effective_covered_through,
        )

    @router.get(
        "/recurrence/attendances",
        response_model=AttendanceListResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        summary="Consulta fatos de atendimento persistidos",
        description=(
            "Datas inclusivas filtram occurred_at. A resposta não deriva "
            "elegibilidade nem reincidência."
        ),
    )
    async def get_attendances(
        operator_id: Annotated[
            str | None, Query(min_length=1, max_length=128)
        ] = None,
        customer_code: Annotated[
            str | None, Query(min_length=1, max_length=128)
        ] = None,
        source: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        channel: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AttendanceListResponse | JSONResponse:
        try:
            filters = AttendanceFilters(
                operator_id=operator_id,
                customer_code=customer_code,
                source=source,
                channel=channel,
                start_date=start_date,
                end_date=end_date,
            )
        except ValueError:
            return _invalid_filters()
        try:
            result = attendance_query.execute(filters)
        except Exception:
            return error_response(
                500, "internal_error", "Attendances could not be retrieved"
            )
        return _attendance_list_response(result)

    @router.get(
        "/recurrence/summary",
        response_model=RecurrenceSummaryResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        summary="Calcula a reincidência factual de uma coorte mensal fechada",
        description=(
            "reference_month usa YYYY-MM. observed_through deve cobrir o último "
            "dia da coorte mais 30 dias. A taxa usa somente atendimentos elegíveis."
        ),
    )
    async def get_recurrence_summary(
        reference_month: str,
        observed_through: date,
        operator_id: Annotated[
            str | None, Query(min_length=1, max_length=128)
        ] = None,
        source: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        channel: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    ) -> RecurrenceSummaryResponse | JSONResponse:
        try:
            month = datetime.strptime(reference_month, "%Y-%m").date().replace(day=1)
            query = RecurrenceCohortQuery(
                reference_month=month,
                observed_through=observed_through,
                operator_id=operator_id,
                source=source,
                channel=channel,
            )
        except ValueError:
            return _invalid_filters()
        try:
            result = summary.execute(query)
        except Exception:
            return error_response(
                500, "internal_error", "Recurrence summary could not be retrieved"
            )
        return _summary_response(result)

    return router


def _invalid_filters() -> JSONResponse:
    return error_response(
        422, "invalid_recurrence_filters", "Recurrence filters are invalid"
    )


def _classification_response(
    value: ClassificationIdentity,
) -> ClassificationIdentityResponse:
    return ClassificationIdentityResponse(
        code=value.code, description=value.description
    )


def _attendance_list_response(result: GetAttendancesResult) -> AttendanceListResponse:
    return AttendanceListResponse(
        filters=AttendanceFiltersResponse(
            operator_id=result.filters.operator_id,
            customer_code=result.filters.customer_code,
            source=result.filters.source,
            channel=result.filters.channel,
            start_date=result.filters.start_date,
            end_date=result.filters.end_date,
        ),
        attendance_count=len(result.items),
        items=[
            AttendanceResponse(
                attendance_id=item.attendance_id,
                external_reference=item.external_reference,
                source=item.source,
                customer_code=item.customer_code,
                operator_id=item.operator_id,
                channel=item.channel,
                occurred_at=item.occurred_at,
                process=_classification_response(item.process),
                opening_classification=_classification_response(
                    item.opening_classification
                ),
                closing_classification=_classification_response(
                    item.closing_classification
                ),
                created_at=item.created_at,
            )
            for item in result.items
        ],
    )


def _summary_response(
    result: GetRecurrenceSummaryResult,
) -> RecurrenceSummaryResponse:
    return RecurrenceSummaryResponse(
        cohort=RecurrenceCohortResponse(
            reference_month=result.query.reference_month,
            cohort_end=result.query.cohort_end,
            window_end=result.query.window_end,
            observed_through=result.query.observed_through,
            operator_id=result.query.operator_id,
            source=result.query.source,
            channel=result.query.channel,
        ),
        eligible_attendance_count=result.eligible_attendance_count,
        recurrence_count=result.recurrence_count,
        recurrence_rate=(
            None
            if result.recurrence_rate is None
            else decimal_string(result.recurrence_rate)
        ),
        by_operator=[
            RecurrenceOperatorSummaryResponse(
                operator_id=item.operator_id,
                eligible_attendance_count=item.eligible_attendance_count,
                recurrence_count=item.recurrence_count,
                recurrence_rate=(
                    None
                    if item.recurrence_rate is None
                    else decimal_string(item.recurrence_rate)
                ),
            )
            for item in result.by_operator
        ],
        occurrences=[
            RecurrenceOccurrenceResponse(
                original_attendance_id=item.original_attendance_id,
                recurrent_attendance_id=item.recurrent_attendance_id,
                customer_code=item.customer_code,
                attributed_operator_id=item.attributed_operator_id,
                original_date=item.original_date,
                recurrent_date=item.recurrent_date,
                days_between=item.days_between,
            )
            for item in result.occurrences
        ],
    )
