from datetime import date, time
from typing import Annotated, Protocol
from uuid import uuid4

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.schemas import ErrorResponse
from supervisor_ai.application.errors import (
    OperationalCollaboratorProfileNotFound,
    WorkScheduleConflict,
)
from supervisor_ai.application.persistence import DailyWorkScheduleOverride
from supervisor_ai.application.use_cases import (
    GetOperationalWorkSchedulesQuery,
    GetOperationalWorkSchedulesResult,
    RecordDailyWorkScheduleOverrideCommand,
)

MVP_MANUAL_OVERRIDE_ACTOR = "mvp-supervisor"


class WorkScheduleQueryContract(Protocol):
    def execute(
        self, query: GetOperationalWorkSchedulesQuery
    ) -> GetOperationalWorkSchedulesResult: ...


class WorkScheduleOverrideContract(Protocol):
    def execute(
        self, command: RecordDailyWorkScheduleOverrideCommand
    ) -> DailyWorkScheduleOverride: ...


class OverrideRequest(BaseModel):
    collaborator_id: str = Field(min_length=1, max_length=128)
    work_date: date
    planned_start: time
    planned_end: time
    reason: str = Field(min_length=1, max_length=500)


def work_schedules_router(
    query_service: WorkScheduleQueryContract,
    override_service: WorkScheduleOverrideContract,
) -> APIRouter:
    router = APIRouter(prefix="/work-schedules", tags=["work-schedules"])

    @router.get(
        "",
        response_model=None,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    )
    async def list_work_schedules(
        competence_month: str,
        collaborator_id: Annotated[str | None, Query(min_length=1)] = None,
        resolution_status: str | None = None,
    ) -> dict[str, object] | JSONResponse:
        try:
            month = date.fromisoformat(f"{competence_month}-01")
            result = query_service.execute(
                GetOperationalWorkSchedulesQuery(
                    month, collaborator_id, resolution_status
                )
            )
        except ValueError:
            return error_response(
                422,
                "invalid_work_schedule_filters",
                "Work schedule filters are invalid",
            )
        except Exception:
            return error_response(
                500, "internal_error", "Work schedules could not be retrieved"
            )
        return {
            "competence_month": result.competence_month.strftime("%Y-%m"),
            "filters": {
                "collaborator_id": result.collaborator_id,
                "resolution_status": result.resolution_status,
            },
            "total_count": result.total_count,
            "pending_count": result.pending_count,
            "items": [_item(item) for item in result.items],
        }

    @router.post(
        "/overrides",
        status_code=201,
        response_model=None,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def create_override(
        payload: OverrideRequest,
    ) -> dict[str, object] | JSONResponse:
        try:
            item = override_service.execute(
                RecordDailyWorkScheduleOverrideCommand(
                    f"schedule-override-{uuid4()}",
                    payload.collaborator_id,
                    payload.work_date,
                    payload.planned_start,
                    payload.planned_end,
                    payload.reason,
                    MVP_MANUAL_OVERRIDE_ACTOR,
                )
            )
        except WorkScheduleConflict:
            return error_response(
                409,
                "work_schedule_override_conflict",
                "A different override already exists for this collaborator and date",
            )
        except OperationalCollaboratorProfileNotFound:
            return error_response(
                404, "collaborator_not_found", "Collaborator was not found"
            )
        except ValueError:
            return error_response(
                422,
                "invalid_work_schedule_override",
                "Work schedule override is invalid",
            )
        except Exception:
            return error_response(
                500, "internal_error", "Work schedule override could not be created"
            )
        return _override(item)

    return router


def _item(item: object) -> dict[str, object]:
    return {
        "collaborator_id": item.collaborator_id,
        "display_name": item.display_name,
        "work_date": item.work_date.isoformat(),
        "planned_start": _time(item.planned_start),
        "planned_end": _time(item.planned_end),
        "resolution_status": item.resolution_status,
        "effective_origin": item.effective_origin,
        "source": item.source,
        "source_reference": item.source_reference,
        "source_sheet": item.source_sheet,
        "source_cell": item.source_cell,
        "unresolved_reason": item.unresolved_reason,
        "has_override": item.has_override,
        "override": None if item.override is None else _override(item.override),
    }


def _override(item: DailyWorkScheduleOverride) -> dict[str, object]:
    return {
        "id": item.id,
        "collaborator_id": item.collaborator_id,
        "work_date": item.work_date.isoformat(),
        "planned_start": _time(item.planned_start),
        "planned_end": _time(item.planned_end),
        "reason": item.reason,
        "created_by": item.created_by,
        "created_at": item.created_at.isoformat(),
    }


def _time(value: time | None) -> str | None:
    return None if value is None else value.strftime("%H:%M:%S")
