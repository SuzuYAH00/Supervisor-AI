from datetime import date
from typing import Annotated, Protocol

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.schemas import (
    CommercialEventProcessingHealthResponse,
    ErrorResponse,
    ProcessingHealthFiltersResponse,
    ProcessingHealthResponse,
    ProcessingRunHealthResponse,
    ProcessingRunStatusCountResponse,
    ProcessingRunVersionCountResponse,
)
from supervisor_ai.application.use_cases import (
    GetProcessingHealthQuery,
    GetProcessingHealthResult,
)


class ProcessingHealthServiceContract(Protocol):
    def execute(self, query: GetProcessingHealthQuery) -> GetProcessingHealthResult: ...


def processing_router(service: ProcessingHealthServiceContract) -> APIRouter:
    router = APIRouter(tags=["processing"])

    @router.get(
        "/processing/health",
        response_model=ProcessingHealthResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        summary="Consulta métricas factuais do processamento persistido",
        description=(
            "Diferente de /health, esta visão consulta a persistência. Datas são "
            "inclusivas sobre ProcessingRun.started_at e não há diagnóstico."
        ),
    )
    async def processing_health(
        start_date: date | None = None,
        end_date: date | None = None,
        source: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        rules_engine_version: Annotated[
            str | None, Query(min_length=1, max_length=100)
        ] = None,
    ) -> ProcessingHealthResponse | JSONResponse:
        try:
            query = GetProcessingHealthQuery(
                start_date=start_date,
                end_date=end_date,
                source=source,
                rules_engine_version=rules_engine_version,
            )
        except ValueError:
            return error_response(
                422,
                "invalid_processing_health_filters",
                "Processing health filters are invalid",
            )
        try:
            result = service.execute(query)
        except Exception:
            return error_response(
                500,
                "internal_error",
                "Processing health could not be retrieved",
            )
        return _project_health(result)

    return router


def _project_health(result: GetProcessingHealthResult) -> ProcessingHealthResponse:
    return ProcessingHealthResponse(
        filters=ProcessingHealthFiltersResponse(
            start_date=result.filters.start_date,
            end_date=result.filters.end_date,
            source=result.filters.source,
            rules_engine_version=result.filters.rules_engine_version,
        ),
        processing_runs=ProcessingRunHealthResponse(
            total=result.processing_runs.total,
            by_final_status=[
                ProcessingRunStatusCountResponse(
                    final_status=item.value,
                    count=item.count,
                )
                for item in result.processing_runs.by_final_status
            ],
            by_rules_engine_version=[
                ProcessingRunVersionCountResponse(
                    rules_engine_version=item.value,
                    count=item.count,
                )
                for item in result.processing_runs.by_rules_engine_version
            ],
        ),
        commercial_events=CommercialEventProcessingHealthResponse(
            events_with_processing_runs=(
                result.commercial_events.events_with_processing_runs
            ),
            events_without_processing_runs=(
                result.commercial_events.events_without_processing_runs
            ),
            events_with_multiple_processing_runs=(
                result.commercial_events.events_with_multiple_processing_runs
            ),
            events_with_ledger_entries=(
                result.commercial_events.events_with_ledger_entries
            ),
            events_without_ledger_entries=(
                result.commercial_events.events_without_ledger_entries
            ),
        ),
    )
