from datetime import date
from typing import Annotated, Protocol

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import JSONResponse

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.projections import decimal_string
from supervisor_ai.api.schemas import (
    CsatEvaluationListResponse,
    CsatEvaluationResponse,
    CsatFiltersResponse,
    CsatImportResponse,
    CsatSummaryGroupResponse,
    CsatSummaryResponse,
    ErrorResponse,
)
from supervisor_ai.application import CsatEvaluationConflict, CsatFilters
from supervisor_ai.application.use_cases import (
    GetCsatEvaluationsResult,
    GetCsatSummaryResult,
    ImportCsatEvaluationsResult,
)
from supervisor_ai.infrastructure.importing import (
    CsatCsvStructureError,
    CsatCsvValidationError,
)


class CsatCsvImportServiceContract(Protocol):
    def import_csv(self, content: str) -> ImportCsatEvaluationsResult: ...


class CsatEvaluationQueryServiceContract(Protocol):
    def execute(self, query: CsatFilters) -> GetCsatEvaluationsResult: ...


class CsatSummaryServiceContract(Protocol):
    def execute(self, query: CsatFilters) -> GetCsatSummaryResult: ...


def csat_router(
    importer: CsatCsvImportServiceContract,
    evaluation_query: CsatEvaluationQueryServiceContract,
    summary: CsatSummaryServiceContract,
) -> APIRouter:
    router = APIRouter(tags=["csat"])

    @router.post(
        "/imports/csat/csv",
        response_model=CsatImportResponse,
        responses={
            400: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        summary="Importa avaliações CSAT factuais de um CSV local",
        description=(
            "Importa fatos sem integração direta com NPX ou MKBot. "
            "A idempotência usa source e external_reference."
        ),
    )
    async def import_csat_csv(
        file: Annotated[UploadFile, File()],
    ) -> CsatImportResponse | JSONResponse:
        if not file.filename:
            return error_response(
                422, "invalid_csat_upload", "CSAT CSV filename is required"
            )
        try:
            content_bytes = await file.read()
        except Exception:
            return error_response(
                500, "csat_upload_read_error", "CSAT CSV upload could not be read"
            )
        if not content_bytes:
            return error_response(
                422, "empty_csat_upload", "CSAT CSV file must not be empty"
            )
        try:
            content = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            return error_response(
                422,
                "invalid_csat_encoding",
                "CSAT CSV file must use UTF-8 encoding",
            )
        try:
            result = importer.import_csv(content)
        except CsatCsvStructureError:
            return error_response(
                400, "csat_csv_structure_error", "CSAT CSV structure is invalid"
            )
        except CsatCsvValidationError:
            return error_response(
                422, "invalid_csat_data", "CSAT CSV contains invalid data"
            )
        except CsatEvaluationConflict:
            return error_response(
                409,
                "csat_evaluation_conflict",
                "CSAT evaluation conflicts with persisted facts",
            )
        except Exception:
            return error_response(
                500, "internal_error", "CSAT CSV import could not be completed"
            )
        return CsatImportResponse(
            received_count=result.received_count,
            created_count=result.created_count,
            already_existing_count=result.already_existing_count,
            evaluation_ids=list(result.evaluation_ids),
        )

    @router.get(
        "/csat/evaluations",
        response_model=CsatEvaluationListResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        summary="Consulta avaliações CSAT factuais persistidas",
        description=(
            "Datas inclusivas filtram evaluated_at. A nota é uma string decimal "
            "e nenhuma escala ou classificação é inferida."
        ),
    )
    async def get_csat_evaluations(
        collaborator_id: Annotated[
            str | None, Query(min_length=1, max_length=128)
        ] = None,
        start_date: date | None = None,
        end_date: date | None = None,
        source: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        channel: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    ) -> CsatEvaluationListResponse | JSONResponse:
        filters = _filters(collaborator_id, start_date, end_date, source, channel)
        if isinstance(filters, JSONResponse):
            return filters
        try:
            result = evaluation_query.execute(filters)
        except Exception:
            return error_response(
                500, "internal_error", "CSAT evaluations could not be retrieved"
            )
        return _evaluation_response(result)

    @router.get(
        "/csat/summary",
        response_model=CsatSummaryResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        summary="Resume fatos CSAT persistidos",
        description=(
            "Retorna contagem e média aritmética factual, agrupadas por "
            "colaborador e canal, sem meta ou diagnóstico."
        ),
    )
    async def get_csat_summary(
        collaborator_id: Annotated[
            str | None, Query(min_length=1, max_length=128)
        ] = None,
        start_date: date | None = None,
        end_date: date | None = None,
        source: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        channel: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    ) -> CsatSummaryResponse | JSONResponse:
        filters = _filters(collaborator_id, start_date, end_date, source, channel)
        if isinstance(filters, JSONResponse):
            return filters
        try:
            result = summary.execute(filters)
        except Exception:
            return error_response(
                500, "internal_error", "CSAT summary could not be retrieved"
            )
        return _summary_response(result)

    return router


def _filters(
    collaborator_id: str | None,
    start_date: date | None,
    end_date: date | None,
    source: str | None,
    channel: str | None,
) -> CsatFilters | JSONResponse:
    try:
        return CsatFilters(
            collaborator_id=collaborator_id,
            start_date=start_date,
            end_date=end_date,
            source=source,
            channel=channel,
        )
    except ValueError:
        return error_response(
            422, "invalid_csat_filters", "CSAT filters are invalid"
        )


def _filter_response(filters: CsatFilters) -> CsatFiltersResponse:
    return CsatFiltersResponse(
        collaborator_id=filters.collaborator_id,
        start_date=filters.start_date,
        end_date=filters.end_date,
        source=filters.source,
        channel=filters.channel,
    )


def _evaluation_response(
    result: GetCsatEvaluationsResult,
) -> CsatEvaluationListResponse:
    return CsatEvaluationListResponse(
        filters=_filter_response(result.filters),
        evaluation_count=result.evaluation_count,
        items=[
            CsatEvaluationResponse(
                evaluation_id=item.evaluation_id,
                external_reference=item.external_reference,
                source=item.source,
                collaborator_id=item.collaborator_id,
                channel=item.channel,
                score=decimal_string(item.score),
                evaluated_at=item.evaluated_at,
                created_at=item.created_at,
            )
            for item in result.items
        ],
    )


def _summary_response(result: GetCsatSummaryResult) -> CsatSummaryResponse:
    return CsatSummaryResponse(
        filters=_filter_response(result.filters),
        evaluation_count=result.evaluation_count,
        score_average=(
            None
            if result.score_average is None
            else decimal_string(result.score_average)
        ),
        by_collaborator=[
            CsatSummaryGroupResponse(
                value=item.value,
                evaluation_count=item.evaluation_count,
                score_average=decimal_string(item.score_average),
            )
            for item in result.by_collaborator
        ],
        by_channel=[
            CsatSummaryGroupResponse(
                value=item.value,
                evaluation_count=item.evaluation_count,
                score_average=decimal_string(item.score_average),
            )
            for item in result.by_channel
        ],
    )
