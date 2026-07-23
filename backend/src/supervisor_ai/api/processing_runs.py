from datetime import date
from typing import Annotated, Protocol

from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.pagination import (
    InvalidPaginationCursor,
    decode_processing_run_cursor,
    encode_processing_run_cursor,
)
from supervisor_ai.api.schemas import (
    ErrorResponse,
    ProcessingRunCommercialEventResponse,
    ProcessingRunDetailsResponse,
    ProcessingRunListItemResponse,
    ProcessingRunListResponse,
    ProcessingRunPhaseResponse,
    ProcessingRunResponse,
)
from supervisor_ai.application import ProcessingRunNotFound
from supervisor_ai.application.use_cases import (
    GetProcessingRunDetailsQuery,
    GetProcessingRunDetailsResult,
    ListProcessingRunsQuery,
    ListProcessingRunsResult,
)


class ProcessingRunDetailsServiceContract(Protocol):
    def execute(
        self, query: GetProcessingRunDetailsQuery
    ) -> GetProcessingRunDetailsResult: ...


class ProcessingRunListServiceContract(Protocol):
    def execute(self, query: ListProcessingRunsQuery) -> ListProcessingRunsResult: ...


def processing_runs_router(
    service: ProcessingRunDetailsServiceContract,
    list_service: ProcessingRunListServiceContract,
) -> APIRouter:
    router = APIRouter(tags=["processing runs"])

    @router.get(
        "/processing-runs",
        response_model=ProcessingRunListResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        summary="Lista execuções persistidas para investigação",
        description=(
            "Ordena por started_at e processing_run_id decrescentes. Datas são "
            "inclusivas em UTC e os mesmos filtros devem acompanhar o cursor."
        ),
    )
    async def list_processing_runs(
        source: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        external_reference: Annotated[
            str | None, Query(min_length=1, max_length=255)
        ] = None,
        final_status: Annotated[
            str | None, Query(min_length=1, max_length=100)
        ] = None,
        rules_engine_version: Annotated[
            str | None, Query(min_length=1, max_length=100)
        ] = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
    ) -> ProcessingRunListResponse | JSONResponse:
        try:
            after = (
                None if cursor is None else decode_processing_run_cursor(cursor)
            )
            query = ListProcessingRunsQuery(
                source=source,
                external_reference=external_reference,
                final_status=final_status,
                rules_engine_version=rules_engine_version,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                after=after,
            )
        except (InvalidPaginationCursor, ValueError):
            return error_response(
                422,
                "invalid_processing_run_filters",
                "Processing run filters are invalid",
            )
        try:
            result = list_service.execute(query)
        except Exception:
            return error_response(
                500,
                "internal_error",
                "Processing runs could not be retrieved",
            )
        return _project_list(result)

    @router.get(
        "/processing-runs/{processing_run_id}",
        response_model=ProcessingRunDetailsResponse,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        summary="Consulta a trilha persistida de uma execução",
        description=(
            "Retorna a execução, seu evento e metadados allowlisted das fases "
            "na ordem persistida. Não reexecuta regras."
        ),
    )
    async def processing_run_details(
        processing_run_id: Annotated[str, Path(min_length=1, max_length=128)],
    ) -> ProcessingRunDetailsResponse | JSONResponse:
        try:
            query = GetProcessingRunDetailsQuery(processing_run_id)
        except ValueError:
            return error_response(
                422,
                "invalid_processing_run_id",
                "Processing run ID is invalid",
            )
        try:
            result = service.execute(query)
        except ProcessingRunNotFound:
            return error_response(
                404,
                "processing_run_not_found",
                "Processing run was not found",
            )
        except Exception:
            return error_response(
                500,
                "internal_error",
                "Processing run details could not be retrieved",
            )
        return _project_details(result)

    return router


def _project_list(result: ListProcessingRunsResult) -> ProcessingRunListResponse:
    return ProcessingRunListResponse(
        items=[
            ProcessingRunListItemResponse(
                processing_run_id=item.processing_run_id,
                event_id=item.event_id,
                source=item.source,
                external_reference=item.external_reference,
                started_at=item.started_at,
                completed_at=item.completed_at,
                final_status=item.final_status,
                rules_engine_version=item.rules_engine_version,
            )
            for item in result.items
        ],
        next_cursor=(
            None
            if result.next_cursor_position is None
            else encode_processing_run_cursor(result.next_cursor_position)
        ),
    )


def _project_details(
    result: GetProcessingRunDetailsResult,
) -> ProcessingRunDetailsResponse:
    run = result.processing_run
    event = result.commercial_event
    return ProcessingRunDetailsResponse(
        processing_run=ProcessingRunResponse(
            processing_run_id=run.processing_run_id,
            event_id=run.event_id,
            final_status=run.final_status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            rules_engine_version=run.rules_engine_version,
            created_at=run.created_at,
        ),
        commercial_event=ProcessingRunCommercialEventResponse(
            event_id=event.event_id,
            external_reference=event.external_reference,
            source=event.source,
            occurred_at=event.occurred_at,
        ),
        phases=[
            ProcessingRunPhaseResponse(
                phase=phase.phase,
                status=phase.status,
                can_continue=phase.can_continue,
            )
            for phase in result.phases
        ],
    )
