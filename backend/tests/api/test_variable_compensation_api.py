import asyncio
from datetime import date
from decimal import Decimal

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from supervisor_ai.api.variable_compensation import variable_compensation_router
from supervisor_ai.application.use_cases import (
    ClosureIssueComponent,
    ClosureIssueScope,
    ClosureIssueSeverity,
    ClosurePendingIssue,
    GetMonthlyVariableCompensationClosureResult,
)


class StubService:
    def __init__(self, result):
        self.result = result
        self.queries = []

    def execute(self, query):
        self.queries.append(query)
        return self.result


def request(app: FastAPI, path: str):
    async def execute():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get(path)

    return asyncio.run(execute())


def test_structured_global_issue_is_projected_with_operational_message():
    issue = ClosurePendingIssue(
        "recurrence_coverage_incomplete",
        ClosureIssueComponent.RECURRENCE,
        ClosureIssueScope.COMPETENCE,
        date(2026, 8, 1),
        "A janela de observação da Reincidência ainda não possui cobertura completa.",
        ClosureIssueSeverity.BLOCKING,
        affected_collaborator_ids=("operator-1", "operator-2"),
        action_type="review_recurrence_import",
    )
    service = StubService(
        GetMonthlyVariableCompensationClosureResult(
            date(2026, 8, 1), 2, 0, 2, None, (), (issue,)
        )
    )
    app = FastAPI()
    app.include_router(variable_compensation_router(service))

    response = request(
        app, "/variable-compensation?competence_month=2026-08&status=incomplete"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["issue_summary"] == {
        "total_count": 1,
        "blocking_count": 1,
        "by_component": {"recurrence": 1},
    }
    assert payload["issues"][0]["code"] == "recurrence_coverage_incomplete"
    assert payload["issues"][0]["scope"] == "competence"
    assert payload["issues"][0]["action_target"] is None
    assert service.queries[0].competence_month == date(2026, 8, 1)


def test_competence_without_issues_returns_empty_central():
    service = StubService(
        GetMonthlyVariableCompensationClosureResult(
            date(2026, 8, 1), 0, 0, 0, Decimal("0.00"), (), ()
        )
    )
    app = FastAPI()
    app.include_router(variable_compensation_router(service))

    response = request(app, "/variable-compensation?competence_month=2026-08")

    assert response.status_code == 200
    assert response.json()["issues"] == []
    assert response.json()["issue_summary"]["blocking_count"] == 0
