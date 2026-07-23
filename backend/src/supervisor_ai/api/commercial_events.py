from datetime import date
from typing import Annotated, Protocol

from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.pagination import (
    InvalidPaginationCursor,
    decode_cursor,
    encode_cursor,
)
from supervisor_ai.api.projections import decimal_string
from supervisor_ai.api.schemas import (
    CommercialEventDetailsResponse,
    CommercialEventLedgerEntryResponse,
    CommercialEventListFiltersResponse,
    CommercialEventListResponse,
    CommercialEventProcessingRunResponse,
    CommercialEventResponse,
    CursorPageResponse,
    ErrorResponse,
)
from supervisor_ai.application import CommercialEventNotFound
from supervisor_ai.application.use_cases import (
    GetCommercialEventDetailsQuery,
    GetCommercialEventDetailsResult,
    ListCommercialEventsQuery,
    ListCommercialEventsResult,
)


class CommercialEventDetailsServiceContract(Protocol):
    def execute(
        self, query: GetCommercialEventDetailsQuery
    ) -> GetCommercialEventDetailsResult: ...


class CommercialEventListServiceContract(Protocol):
    def execute(
        self, query: ListCommercialEventsQuery
    ) -> ListCommercialEventsResult: ...


def commercial_events_router(
    service: CommercialEventDetailsServiceContract,
    list_service: CommercialEventListServiceContract,
) -> APIRouter:
    router = APIRouter(tags=["commercial events"])

    @router.get(
        "/commercial-events",
        response_model=CommercialEventListResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        summary="Lista eventos comerciais persistidos",
        description=(
            "Ordena por occurred_at e event_id decrescentes. Datas UTC são "
            "inclusivas e o cursor exige a repetição dos mesmos filtros."
        ),
    )
    async def list_commercial_events(
        source: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        external_reference: Annotated[
            str | None, Query(min_length=1, max_length=255)
        ] = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
    ) -> CommercialEventListResponse | JSONResponse:
        try:
            after = None if cursor is None else decode_cursor(cursor)
        except InvalidPaginationCursor:
            return error_response(
                422,
                "invalid_cursor",
                "Pagination cursor is invalid",
            )
        try:
            query = ListCommercialEventsQuery(
                source=source,
                external_reference=external_reference,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                after=after,
            )
        except ValueError:
            return error_response(
                422,
                "invalid_commercial_event_filters",
                "Commercial event filters are invalid",
            )
        try:
            result = list_service.execute(query)
        except Exception:
            return error_response(
                500,
                "internal_error",
                "Commercial events could not be retrieved",
            )
        return _project_list(result)

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
            return error_response(
                422,
                "invalid_commercial_event_id",
                "Commercial event ID is invalid",
            )
        try:
            result = service.execute(query)
        except CommercialEventNotFound:
            return error_response(
                404,
                "commercial_event_not_found",
                "Commercial event was not found",
            )
        except Exception:
            return error_response(
                500,
                "internal_error",
                "Commercial event details could not be retrieved",
            )
        return _project_details(result)

    return router


def _project_list(result: ListCommercialEventsResult) -> CommercialEventListResponse:
    return CommercialEventListResponse(
        filters=CommercialEventListFiltersResponse(
            source=result.filters.source,
            external_reference=result.filters.external_reference,
            start_date=result.filters.start_date,
            end_date=result.filters.end_date,
        ),
        page=CursorPageResponse(
            limit=result.filters.limit,
            next_cursor=(
                None
                if result.next_cursor_position is None
                else encode_cursor(result.next_cursor_position)
            ),
            has_more=result.has_more,
        ),
        items=[
            CommercialEventResponse(
                event_id=item.event_id,
                external_reference=item.external_reference,
                source=item.source,
                occurred_at=item.occurred_at,
                received_at=item.received_at,
                created_at=item.created_at,
            )
            for item in result.items
        ],
    )


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
