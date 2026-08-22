from datetime import UTC, date, datetime, time
from typing import Annotated, Protocol
from uuid import uuid4

from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.schemas import ErrorResponse
from supervisor_ai.application.errors import (
    DelayOccurrenceNotFound,
    DelayReviewConflict,
)
from supervisor_ai.application.persistence import DelayReview
from supervisor_ai.application.use_cases import (
    GetOperationalDelaysQuery,
    GetOperationalDelaysResult,
    RecordDelayReviewCommand,
)
from supervisor_ai.rules_engine.delays import DelayDecision

MVP_DELAY_REVIEW_ACTOR = "mvp-supervisor"


class OperationalDelayQueryContract(Protocol):
    def execute(
        self, query: GetOperationalDelaysQuery
    ) -> GetOperationalDelaysResult: ...


class DelayReviewContract(Protocol):
    def execute(self, command: RecordDelayReviewCommand) -> DelayReview: ...


class DelayReviewRequest(BaseModel):
    decision: DelayDecision
    employee_occurrence_report_id: str | None = Field(
        default=None, min_length=1, max_length=128
    )
    note: str | None = Field(default=None, min_length=1, max_length=2000)


def delays_router(
    query_service: OperationalDelayQueryContract, review_service: DelayReviewContract
) -> APIRouter:
    router = APIRouter(prefix="/delays", tags=["delays"])

    @router.get(
        "",
        response_model=None,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    )
    async def list_delays(
        competence_month: str,
        collaborator_id: Annotated[str | None, Query(min_length=1)] = None,
        delay_type: str | None = None,
        review_status: str | None = None,
    ) -> dict[str, object] | JSONResponse:
        try:
            month = date.fromisoformat(f"{competence_month}-01")
            result = query_service.execute(
                GetOperationalDelaysQuery(
                    month, collaborator_id, delay_type, review_status
                )
            )
        except ValueError:
            return error_response(
                422, "invalid_delay_filters", "Delay filters are invalid"
            )
        except Exception:
            return error_response(
                500, "internal_error", "Operational delays could not be retrieved"
            )
        return _result(result)

    @router.post(
        "/{delay_occurrence_id}/reviews",
        status_code=201,
        response_model=None,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def create_review(
        delay_occurrence_id: Annotated[str, Path(min_length=1, max_length=128)],
        payload: DelayReviewRequest,
    ) -> dict[str, object] | JSONResponse:
        now = datetime.now(UTC)
        try:
            review = review_service.execute(
                RecordDelayReviewCommand(
                    f"delay-review-{uuid4()}",
                    delay_occurrence_id,
                    payload.decision,
                    now,
                    MVP_DELAY_REVIEW_ACTOR,
                    payload.employee_occurrence_report_id,
                    payload.note,
                )
            )
        except DelayOccurrenceNotFound:
            return error_response(
                404, "delay_occurrence_not_found", "Delay occurrence was not found"
            )
        except DelayReviewConflict:
            return error_response(
                409,
                "delay_review_conflict",
                "Review evidence does not match the delay occurrence",
            )
        except ValueError:
            return error_response(
                422, "invalid_delay_review", "Delay review is invalid"
            )
        except Exception:
            return error_response(
                500, "internal_error", "Delay review could not be recorded"
            )
        return _review(review)

    return router


def _result(result: GetOperationalDelaysResult) -> dict[str, object]:
    return {
        "competence_month": result.competence_month.strftime("%Y-%m"),
        "filters": {
            "collaborator_id": result.collaborator_id,
            "delay_type": result.delay_type,
            "review_status": result.review_status,
        },
        "detected_count": result.detected_count,
        "pending_count": result.pending_count,
        "valid_count": result.valid_count,
        "corrected_count": result.corrected_count,
        "items": [_item(item) for item in result.items],
    }


def _item(item: object) -> dict[str, object]:
    occurrence, source = item.occurrence, item.source_fact
    return {
        "delay_occurrence_id": occurrence.id,
        "collaborator_id": occurrence.collaborator_id,
        "display_name": item.display_name,
        "occurrence_date": occurrence.occurrence_date.isoformat(),
        "occurrence_type": occurrence.occurrence_type,
        "review_status": item.review_status,
        "counts_for_rv": item.counts_for_rv,
        "created_at": occurrence.created_at.isoformat(),
        "observed_seconds": occurrence.observed_seconds,
        "applied_limit_seconds": occurrence.applied_limit_seconds,
        "source_fact": {
            "type": source.source_fact_type,
            "id": source.source_fact_id,
            "source": source.source,
            "source_reference": source.source_reference,
            "source_extract_reference": source.source_extract_reference,
            "source_sheet": source.source_sheet,
            "source_row": source.source_row,
            "queue": source.queue,
            "started_at": source.started_at.isoformat(),
            "ended_at": source.ended_at.isoformat(),
            "duration_seconds": source.duration_seconds,
            "pause_type": source.pause_type,
        },
        "schedule": None if item.schedule is None else _schedule(item.schedule),
        "review": None if item.current_review is None else _review(item.current_review),
        "possible_employee_occurrence_reports": [
            {
                "id": report.id,
                "external_reference": report.external_reference,
                "source": report.source,
                "external_collaborator_identity": report.external_collaborator_identity,
                "submitted_at": report.submitted_at.isoformat(),
                "occurrence_date": report.occurrence_date.isoformat(),
                "reason_text": report.reason_text,
                "source_sheet": report.source_sheet,
                "source_row": report.source_row,
            }
            for report in item.possible_reports
        ],
    }


def _schedule(schedule: object) -> dict[str, object]:
    return {
        "planned_start": _time(schedule.planned_start),
        "planned_end": _time(schedule.planned_end),
        "effective_origin": schedule.effective_origin,
        "source_reference": schedule.source_reference,
        "source_sheet": schedule.source_sheet,
        "source_cell": schedule.source_cell,
    }


def _review(review: DelayReview) -> dict[str, object]:
    return {
        "id": review.id,
        "decision": review.decision,
        "decided_at": review.decided_at.isoformat(),
        "decided_by": review.decided_by,
        "employee_occurrence_report_id": review.employee_occurrence_report_id,
        "note": review.note,
        "created_at": review.created_at.isoformat(),
    }


def _time(value: time | None) -> str | None:
    return None if value is None else value.strftime("%H:%M:%S")
