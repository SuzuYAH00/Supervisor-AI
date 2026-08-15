import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient, Response

from supervisor_ai.bootstrap import build_http_application, build_session_factory
from supervisor_ai.database.base import Base

HEADER = (
    "evaluation_id,external_reference,source,collaborator_id,channel,score,"
    "evaluated_at\n"
)
ROWS = (
    "csat-1,external-1,mkbot-export,collaborator-1,whatsapp,10,"
    "2026-07-20T12:00:00Z\n"
    "csat-2,external-2,npx-export,collaborator-1,phone,8,"
    "2026-07-21T12:00:00Z\n"
    "csat-3,external-3,mkbot-export,collaborator-2,,6,"
    "2026-08-01T12:00:00Z\n"
)


def request(
    application,
    method: str,
    path: str,
    *,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> Response:
    async def execute() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.request(method, path, files=files)

    return asyncio.run(execute())


def application(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'csat.sqlite3'}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    Base.metadata.create_all(engine)
    return build_http_application(database_url), engine


def test_real_http_flow_is_empty_imports_filters_summarizes_and_is_idempotent(
    tmp_path: Path,
) -> None:
    app, engine = application(tmp_path)

    empty = request(app, "GET", "/csat/evaluations")
    assert empty.status_code == 200
    assert empty.json()["evaluation_count"] == 0
    assert empty.json()["items"] == []
    empty_summary = request(app, "GET", "/csat/summary")
    assert empty_summary.json()["score_average"] is None
    assert empty_summary.json()["by_collaborator"] == []

    first = request(
        app,
        "POST",
        "/imports/csat/csv",
        files={"file": ("csat.csv", (HEADER + ROWS).encode(), "text/csv")},
    )
    assert first.status_code == 200
    assert first.json() == {
        "received_count": 3,
        "created_count": 3,
        "already_existing_count": 0,
        "evaluation_ids": ["csat-1", "csat-2", "csat-3"],
    }

    by_collaborator = request(
        app,
        "GET",
        "/csat/evaluations?collaborator_id=collaborator-1",
    )
    assert by_collaborator.status_code == 200
    assert [item["evaluation_id"] for item in by_collaborator.json()["items"]] == [
        "csat-1",
        "csat-2",
    ]
    assert by_collaborator.json()["items"][0]["score"] == "10.00"

    by_period_and_channel = request(
        app,
        "GET",
        "/csat/evaluations?start_date=2026-07-21&end_date=2026-07-21&channel=phone",
    )
    assert by_period_and_channel.json()["evaluation_count"] == 1
    assert by_period_and_channel.json()["items"][0]["source"] == "npx-export"

    summary = request(app, "GET", "/csat/summary?source=mkbot-export")
    assert summary.status_code == 200
    assert summary.json()["evaluation_count"] == 2
    assert summary.json()["score_average"] == "8.00"
    assert summary.json()["by_collaborator"] == [
        {"value": "collaborator-1", "evaluation_count": 1, "score_average": "10.00"},
        {"value": "collaborator-2", "evaluation_count": 1, "score_average": "6.00"},
    ]

    repeated = request(
        app,
        "POST",
        "/imports/csat/csv",
        files={"file": ("csat.csv", (HEADER + ROWS).encode(), "text/csv")},
    )
    assert repeated.status_code == 200
    assert repeated.json()["created_count"] == 0
    assert repeated.json()["already_existing_count"] == 3
    assert request(app, "GET", "/csat/evaluations").json()["evaluation_count"] == 3

    conflicting_row = (
        "csat-1,external-1,mkbot-export,collaborator-1,whatsapp,9,"
        "2026-07-20T12:00:00Z\n"
    )
    conflict = request(
        app,
        "POST",
        "/imports/csat/csv",
        files={
            "file": ("conflict.csv", (HEADER + conflicting_row).encode(), "text/csv")
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "csat_evaluation_conflict"
    assert request(app, "GET", "/csat/evaluations").json()["evaluation_count"] == 3
    engine.dispose()


def test_http_errors_are_stable_and_safe(tmp_path: Path) -> None:
    app, engine = application(tmp_path)

    missing = request(app, "POST", "/imports/csat/csv")
    invalid = request(
        app,
        "POST",
        "/imports/csat/csv",
        files={"file": ("csat.csv", b"wrong,header\n1,2\n", "text/csv")},
    )
    inverted = request(
        app,
        "GET",
        "/csat/summary?start_date=2026-08-01&end_date=2026-07-01",
    )
    invalid_data = request(
        app,
        "POST",
        "/imports/csat/csv",
        files={
            "file": (
                "invalid.csv",
                (
                    HEADER
                    + "csat-1,ref,source,user,chat,not-a-score,"
                    "2026-07-20T12:00:00Z\n"
                ).encode(),
                "text/csv",
            )
        },
    )

    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "csat_upload_validation_error"
    assert invalid.status_code == 400
    assert invalid.json() == {
        "error": {
            "code": "csat_csv_structure_error",
            "message": "CSAT CSV structure is invalid",
        }
    }
    assert inverted.status_code == 422
    assert inverted.json()["error"]["code"] == "invalid_csat_filters"
    assert invalid_data.status_code == 422
    assert invalid_data.json()["error"]["code"] == "invalid_csat_data"
    serialized = str(
        (missing.json(), invalid.json(), invalid_data.json(), inverted.json())
    ).lower()
    assert "traceback" not in serialized
    assert "sql" not in serialized
    assert "database" not in serialized
    engine.dispose()
