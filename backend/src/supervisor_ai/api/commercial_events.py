from typing import Annotated, Protocol

from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse

from supervisor_ai.api.projections import decimal_string
from supervisor_ai.api.schemas import (
    CommercialEventDetailsResponse,
    CommercialEventLedgerEntryResponse,
    CommercialEventProcessingRunResponse,
    CommercialEventResponse,
    ErrorResponse,
)
from supervisor_ai.application import CommercialEventNotFound
from supervisor_ai.application.use_cases import (
    GetCommercialEventDetailsQuery,
    GetCommercialEventDetailsResult,
)


class CommercialEventDetailsServiceContract(Protocol):
    def execute(
        self, query: GetCommercialEventDetailsQuery
    ) -> GetCommercialEventDetailsResult: ...


def commercial_events_router(
    service: CommercialEventDetailsServiceContract,
) -> APIRouter:
    router = APIRouter(tags=["commercial events"])

    @router.get(
        "/commercial-events/{commercial_event_id}",
        response_model=CommercialEventDetailsResponse,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        summary="Consulta a trilha de auditoria de um evento comercial",
        description=(
            "Retorna os dados públicos persistidos do evento, seus lançamentos "
            "e todas as execuções. O raw payload não é exposto."
        ),
    )
    async def commercial_event_details(
        commercial_event_id: Annotated[str, Path(min_length=1, max_length=128)],
    ) -> CommercialEventDetailsResponse | JSONResponse:
        try:
            query = GetCommercialEventDetailsQuery(commercial_event_id)
        except ValueError:
            return _error_response(
                422,
                "invalid_commercial_event_id",
                "Commercial event ID is invalid",
            )
        try:
            result = service.execute(query)
        except CommercialEventNotFound:
            return _error_response(
                404,
                "commercial_event_not_found",
                "Commercial event was not found",
            )
        except Exception:
            return _error_response(
                500,
                "internal_error",
                "Commercial event details could not be retrieved",
            )
        return _project_details(result)

    return router


def _project_details(
    result: GetCommercialEventDetailsResult,
) -> CommercialEventDetailsResponse:
    event = result.commercial_event
    return CommercialEventDetailsResponse(
        commercial_event=CommercialEventResponse(
            event_id=event.event_id,
            external_reference=event.external_reference,
            source=event.source,
            occurred_at=event.occurred_at,
            received_at=event.received_at,
            created_at=event.created_at,
        ),
        ledger_entries=[
            CommercialEventLedgerEntryResponse(
                ledger_entry_id=entry.ledger_entry_id,
                event_id=entry.event_id,
                beneficiary_id=entry.beneficiary_id,
                entry_type=entry.entry_type.value,
                amount=decimal_string(entry.amount),
                currency=entry.currency.value,
                posted_at=entry.posted_at,
                posting_reference=entry.posting_reference,
                remuneration_calculation_reference=(
                    entry.remuneration_calculation_reference
                ),
                invoice_id=entry.invoice_id,
                source_reference_ids=list(entry.source_reference_ids),
            )
            for entry in result.ledger_entries
        ],
        processing_runs=[
            CommercialEventProcessingRunResponse(
                processing_run_id=run.processing_run_id,
                event_id=run.event_id,
                final_status=run.final_status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                rules_engine_version=run.rules_engine_version,
                created_at=run.created_at,
            )
            for run in result.processing_runs
        ],
    )


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
