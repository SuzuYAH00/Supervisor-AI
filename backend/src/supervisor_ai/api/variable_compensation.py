from datetime import date
from typing import Annotated, Protocol

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.schemas import ErrorResponse
from supervisor_ai.application.use_cases import (
    ClosureStatus,
    GetMonthlyVariableCompensationClosureQuery,
    GetMonthlyVariableCompensationClosureResult,
)


class VariableCompensationClosureContract(Protocol):
    def execute(
        self, query: GetMonthlyVariableCompensationClosureQuery
    ) -> GetMonthlyVariableCompensationClosureResult: ...


def variable_compensation_router(
    service: VariableCompensationClosureContract,
) -> APIRouter:
    router = APIRouter(prefix="/variable-compensation", tags=["variable-compensation"])

    @router.get(
        "",
        response_model=None,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    )
    async def list_closures(
        competence_month: str,
        collaborator_id: Annotated[str | None, Query(min_length=1)] = None,
        status: ClosureStatus | None = None,
    ) -> dict[str, object] | JSONResponse:
        try:
            month = date.fromisoformat(f"{competence_month}-01")
            result = service.execute(
                GetMonthlyVariableCompensationClosureQuery(
                    month, collaborator_id, status
                )
            )
        except ValueError:
            return error_response(
                422,
                "invalid_variable_compensation_filters",
                "Variable compensation filters are invalid",
            )
        except Exception:
            return error_response(
                500,
                "internal_error",
                "Variable compensation closure could not be retrieved",
            )
        return _result(result)

    return router


def _result(result: GetMonthlyVariableCompensationClosureResult) -> dict[str, object]:
    by_component: dict[str, int] = {}
    for issue in result.issues:
        by_component[issue.component.value] = (
            by_component.get(issue.component.value, 0) + 1
        )
    return {
        "competence_month": result.competence_month.strftime("%Y-%m"),
        "collaborator_count": result.collaborator_count,
        "calculated_count": result.calculated_count,
        "incomplete_count": result.incomplete_count,
        "projected_total": _decimal(result.projected_total),
        "issue_summary": {
            "total_count": len(result.issues),
            "blocking_count": len(result.issues),
            "by_component": by_component,
        },
        "issues": [_issue(issue) for issue in result.issues],
        "items": [_item(item) for item in result.items],
    }


def _item(item: object) -> dict[str, object]:
    return {
        "collaborator_id": item.collaborator_id,
        "display_name": item.display_name,
        "competence_month": item.competence_month.strftime("%Y-%m"),
        "status": item.status.value,
        "pending_reasons": list(item.pending_reasons),
        "pending_issues": [_issue(issue) for issue in item.pending_issues],
        "eligibility": {
            "current_worked_days": item.current_worked_days,
            "previous_worked_days": item.previous_worked_days,
        },
        "csat": {
            **_component(item.csat.result),
            "modality": item.csat.modality,
            "eligible_contact_count": item.csat.eligible_contact_count,
            "valid_response_count": item.csat.valid_response_count,
            "raw_average": _decimal(item.csat.raw_average),
            "response_rate": _decimal(item.csat.response_rate),
            "minimum_response_rate": _decimal(item.csat.minimum_response_rate),
        },
        "recurrence": {
            **_component(item.recurrence.result),
            "eligible_attendance_count": item.recurrence.eligible_attendance_count,
            "recurrence_count": item.recurrence.recurrence_count,
            "team_average_cap_passed": item.recurrence.team_average_cap_passed,
        },
        "delays": {
            "count": item.delays.count,
            "amount": _decimal(item.delays.amount),
        },
        "absences": {
            "count": item.absences.count,
            "amount": _decimal(item.absences.amount),
        },
        "positive_amount": _decimal(item.positive_amount),
        "deductions_amount": _decimal(item.deductions_amount),
        "total_amount": _decimal(item.total_amount),
        "flag": item.flag,
    }


def _component(item: object) -> dict[str, object]:
    return {
        "status": item.status,
        "reference_month": item.reference_month.strftime("%Y-%m"),
        "eligible": item.eligible,
        "tier": item.tier,
        "amount": _decimal(item.amount),
        "individual_value": _decimal(item.individual_value),
        "team_average": _decimal(item.team_average),
    }


def _issue(issue: object) -> dict[str, object]:
    return {
        "code": issue.code,
        "component": issue.component.value,
        "scope": issue.scope.value,
        "collaborator_id": issue.collaborator_id,
        "affected_collaborator_ids": list(issue.affected_collaborator_ids),
        "competence_month": issue.competence_month.strftime("%Y-%m"),
        "message": issue.message,
        "severity": issue.severity.value,
        "blocking": issue.severity.value == "blocking",
        "action_type": issue.action_type,
        "action_target": issue.action_target,
        "metadata": dict(issue.metadata),
    }


def _decimal(value: object) -> str | None:
    return None if value is None else format(value, "f")
