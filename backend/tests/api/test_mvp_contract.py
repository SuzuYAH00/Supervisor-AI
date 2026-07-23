import asyncio
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import Engine

from supervisor_ai.api.schemas import ProcessingRunListItemResponse
from supervisor_ai.bootstrap import build_http_application, build_session_factory
from supervisor_ai.database.base import Base

EXPECTED_ROUTES = {
    ("GET", "/health"),
    ("POST", "/imports/csv"),
    ("GET", "/financial/snapshot"),
    ("GET", "/financial/summary"),
    ("GET", "/commercial-events"),
    ("GET", "/commercial-events/{commercial_event_id}"),
    ("GET", "/collaborators/{collaborator_id}/financial-timeline"),
    ("GET", "/processing-runs"),
    ("GET", "/processing-runs/{processing_run_id}"),
    ("GET", "/processing/health"),
}
def application(tmp_path: Path) -> tuple[FastAPI, Engine]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'mvp-contract.sqlite3'}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)
    return build_http_application(database_url), engine


def request(app: FastAPI, method: str, path: str) -> Response:
    async def execute() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path)

    return asyncio.run(execute())


def test_public_route_inventory_has_no_conflicts_or_duplicates(tmp_path: Path) -> None:
    app, engine = application(tmp_path)
    schema = app.openapi()
    routes = {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        for method in operations
        if method in {"get", "post"}
    }
    operation_ids = [
        operation["operationId"]
        for methods in schema["paths"].values()
        for operation in methods.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]

    assert routes == EXPECTED_ROUTES
    assert len(operation_ids) == len(set(operation_ids)) == len(EXPECTED_ROUTES)
    assert request(app, "GET", "/processing-runs").status_code == 200
    assert request(app, "GET", "/processing-runs/missing").status_code == 404
    assert request(app, "GET", "/commercial-events").status_code == 200
    assert request(app, "GET", "/commercial-events/missing").status_code == 404
    engine.dispose()


def test_openapi_exposes_mvp_models_errors_and_parameter_limits(
    tmp_path: Path,
) -> None:
    app, engine = application(tmp_path)
    schema = app.openapi()
    assert schema["info"]["version"] == "1.0.0"
    assert set(schema["paths"]) == {path for _, path in EXPECTED_ROUTES}
    for methods in schema["paths"].values():
        for operation in methods.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            if "422" in operation["responses"]:
                reference = operation["responses"]["422"]["content"][
                    "application/json"
                ]["schema"]["$ref"]
                assert reference == "#/components/schemas/ErrorResponse"

    processing_parameters = {
        parameter["name"]: parameter
        for parameter in schema["paths"]["/processing-runs"]["get"]["parameters"]
    }
    assert processing_parameters["limit"]["schema"]["minimum"] == 1
    assert processing_parameters["limit"]["schema"]["maximum"] == 100
    assert processing_parameters["start_date"]["schema"]["anyOf"][0]["format"] == (
        "date"
    )
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    assert all(
        forbidden not in schema["components"]["schemas"]
        for forbidden in ("CommercialEventRecord", "ProcessingRunRecord")
    )
    engine.dispose()


def test_error_envelope_covers_validation_not_found_and_method_not_allowed(
    tmp_path: Path,
) -> None:
    app, engine = application(tmp_path)
    validation = request(app, "GET", "/processing-runs?limit=0")
    missing_route = request(app, "GET", "/route-that-does-not-exist")
    missing_resource = request(app, "GET", "/processing-runs/missing")
    method = request(app, "POST", "/health")

    assert validation.status_code == 422
    assert validation.json() == {
        "error": {
            "code": "invalid_query_parameters",
            "message": "Request parameters are invalid",
        }
    }
    assert missing_route.status_code == 404
    assert missing_route.json() == {
        "error": {
            "code": "route_not_found",
            "message": "Requested route was not found",
        }
    }
    assert missing_resource.status_code == 404
    assert missing_resource.json()["error"]["code"] == "processing_run_not_found"
    assert method.status_code == 405
    assert method.json() == {
        "error": {
            "code": "method_not_allowed",
            "message": "HTTP method is not allowed for this route",
        }
    }
    assert "GET" in method.headers["allow"]
    engine.dispose()


def test_empty_read_endpoints_are_stable_and_utc_serialization_is_explicit(
    tmp_path: Path,
) -> None:
    app, engine = application(tmp_path)
    expected_empty = {
        "/financial/snapshot": ("credit_count", 0),
        "/financial/summary": ("collaborator_count", 0),
        "/commercial-events": ("items", []),
        "/collaborators/unknown/financial-timeline": ("items", []),
        "/processing-runs": ("items", []),
        "/processing/health": ("processing_runs", {
            "total": 0,
            "by_final_status": [],
            "by_rules_engine_version": [],
        }),
    }
    for path, (field, expected) in expected_empty.items():
        response = request(app, "GET", path)
        assert response.status_code == 200
        assert response.json()[field] == expected
        assert "raw_payload" not in response.text
        assert "SQLAlchemy" not in response.text
    engine.dispose()


def test_public_datetime_serializes_with_explicit_utc_designator() -> None:
    item = ProcessingRunListItemResponse(
        processing_run_id="run-1",
        event_id="event-1",
        source="csv",
        external_reference="external-1",
        started_at=datetime(2026, 7, 23, 12, tzinfo=UTC),
        completed_at=datetime(2026, 7, 23, 12, 0, 1, tzinfo=UTC),
        final_status="posted",
        rules_engine_version="rules-1",
    )
    serialized = item.model_dump_json()
    assert '"started_at":"2026-07-23T12:00:00Z"' in serialized
    assert '"completed_at":"2026-07-23T12:00:01Z"' in serialized
