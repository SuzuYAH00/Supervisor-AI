from typing import Annotated, Protocol

from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.schemas import (
    ErrorResponse,
    ProcessingRunCommercialEventResponse,
    ProcessingRunDetailsResponse,
    ProcessingRunPhaseResponse,
    ProcessingRunResponse,
)
from supervisor_ai.application import ProcessingRunNotFound
from supervisor_ai.application.use_cases import (
    GetProcessingRunDetailsQuery,
    GetProcessingRunDetailsResult,
)


class ProcessingRunDetailsServiceContract(Protocol):
    def execute(
        self, query: GetProcessingRunDetailsQuery
    ) -> GetProcessingRunDetailsResult: ...


def processing_runs_router(
    service: ProcessingRunDetailsServiceContract,
) -> APIRouter:
    router = APIRouter(tags=["processing runs"])

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
