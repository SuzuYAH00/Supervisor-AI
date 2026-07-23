from datetime import date
from typing import Annotated, Protocol

from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.pagination import (
    InvalidPaginationCursor,
    decode_timeline_cursor,
    encode_timeline_cursor,
)
from supervisor_ai.api.projections import decimal_string
from supervisor_ai.api.schemas import (
    CollaboratorFinancialTimelineItemResponse,
    CollaboratorFinancialTimelineResponse,
    CollaboratorTimelineFiltersResponse,
    CursorPageResponse,
    ErrorResponse,
    TimelineCommercialEventResponse,
)
from supervisor_ai.application.use_cases import (
    GetCollaboratorFinancialTimelineQuery,
    GetCollaboratorFinancialTimelineResult,
)
from supervisor_ai.rules_engine import Currency, LedgerEntryType


class CollaboratorFinancialTimelineServiceContract(Protocol):
    def execute(
        self, query: GetCollaboratorFinancialTimelineQuery
    ) -> GetCollaboratorFinancialTimelineResult: ...


def collaborators_router(
    service: CollaboratorFinancialTimelineServiceContract,
) -> APIRouter:
    router = APIRouter(tags=["collaborators"])

    @router.get(
        "/collaborators/{collaborator_id}/financial-timeline",
        response_model=CollaboratorFinancialTimelineResponse,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
        summary="Consulta a linha do tempo financeira de um colaborador",
        description=(
            "Lista lançamentos reais por posted_at decrescente, com evento de "
            "origem, filtros UTC inclusivos e paginação keyset."
        ),
    )
    async def financial_timeline(
        collaborator_id: Annotated[str, Path(min_length=1, max_length=128)],
        start_date: date | None = None,
        end_date: date | None = None,
        entry_type: LedgerEntryType | None = None,
        currency: Currency | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
    ) -> CollaboratorFinancialTimelineResponse | JSONResponse:
        try:
            after = None if cursor is None else decode_timeline_cursor(cursor)
        except InvalidPaginationCursor:
            return error_response(
                422, "invalid_cursor", "Pagination cursor is invalid"
            )
        try:
            query = GetCollaboratorFinancialTimelineQuery(
                collaborator_id=collaborator_id,
                start_date=start_date,
                end_date=end_date,
                entry_type=entry_type,
                currency=currency,
                limit=limit,
                after=after,
            )
        except ValueError:
            return error_response(
                422,
                "invalid_financial_timeline_filters",
                "Financial timeline filters are invalid",
            )
        try:
            result = service.execute(query)
        except Exception:
            return error_response(
                500,
                "internal_error",
                "Collaborator financial timeline could not be retrieved",
            )
        return _project_timeline(result)

    return router


def _project_timeline(
    result: GetCollaboratorFinancialTimelineResult,
) -> CollaboratorFinancialTimelineResponse:
    return CollaboratorFinancialTimelineResponse(
        collaborator_id=result.filters.collaborator_id,
        filters=CollaboratorTimelineFiltersResponse(
            start_date=result.filters.start_date,
            end_date=result.filters.end_date,
            entry_type=(
                None
                if result.filters.entry_type is None
                else result.filters.entry_type.value
            ),
            currency=(
                None
                if result.filters.currency is None
                else result.filters.currency.value
            ),
        ),
        page=CursorPageResponse(
            limit=result.filters.limit,
            next_cursor=(
                None
                if result.next_cursor_position is None
                else encode_timeline_cursor(result.next_cursor_position)
            ),
            has_more=result.has_more,
        ),
        items=[
            CollaboratorFinancialTimelineItemResponse(
                ledger_entry_id=item.ledger_entry_id,
                posted_at=item.posted_at,
                entry_type=item.entry_type.value,
                amount=decimal_string(item.amount),
                currency=item.currency.value,
                invoice_id=item.invoice_id,
                posting_reference=item.posting_reference,
                remuneration_calculation_reference=(
                    item.remuneration_calculation_reference
                ),
                source_reference_ids=list(item.source_reference_ids),
                commercial_event=TimelineCommercialEventResponse(
                    event_id=item.commercial_event.event_id,
                    external_reference=item.commercial_event.external_reference,
                    source=item.commercial_event.source,
                    occurred_at=item.commercial_event.occurred_at,
                ),
            )
            for item in result.items
        ],
    )
