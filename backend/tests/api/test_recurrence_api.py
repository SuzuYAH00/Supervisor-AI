import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient, Response

from supervisor_ai.bootstrap import build_http_application, build_session_factory
from supervisor_ai.database.base import Base

HEADER = (
    "attendance_id,external_reference,source,customer_code,operator_id,channel,"
    "occurred_at,process_code,process_description,opening_code,"
    "opening_description,closing_code,closing_description\n"
)
ROWS = (
    "original,protocol-1,local-export,customer-1,operator-original,phone,"
    "2026-07-31T23:00:00Z,01,Atendimento Suporte,001,Sem acesso a internet,"
    "001,Dispositivo Cliente\n"
    "return,protocol-2,local-export,customer-1,operator-return,whatsapp,"
    "2026-08-01T01:00:00Z,01,Atendimento Suporte,002,Lentidão,"
    "029,Roteador Reiniciado\n"
    "general,protocol-3,local-export,customer-2,operator-original,phone,"
    "2026-07-15T12:00:00Z,02,Outro processo,001,Sem acesso a internet,"
    "001,Dispositivo Cliente\n"
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
    database_url = f"sqlite+pysqlite:///{tmp_path / 'recurrence.sqlite3'}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    Base.metadata.create_all(engine)
    return build_http_application(database_url), engine


def test_real_http_flow_imports_queries_calculates_and_is_idempotent(
    tmp_path: Path,
) -> None:
    app, engine = application(tmp_path)
    empty = request(app, "GET", "/recurrence/attendances")
    assert empty.status_code == 200
    assert empty.json()["items"] == []

    first = request(
        app,
        "POST",
        "/imports/recurrence/attendances/csv",
        files={"file": ("attendances.csv", (HEADER + ROWS).encode(), "text/csv")},
    )
    assert first.status_code == 200
    assert first.json()["created_count"] == 3

    filtered = request(
        app,
        "GET",
        "/recurrence/attendances?customer_code=customer-1&channel=phone",
    )
    assert filtered.status_code == 200
    assert filtered.json()["attendance_count"] == 1
    assert filtered.json()["items"][0]["opening_classification"] == {
        "code": "001",
        "description": "Sem acesso a internet",
    }
    assert "raw_payload" not in filtered.text

    summary = request(
        app,
        "GET",
        "/recurrence/summary?reference_month=2026-07&observed_through=2026-08-30",
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["eligible_attendance_count"] == 1
    assert body["recurrence_count"] == 1
    assert body["recurrence_rate"] == "1.00"
    assert body["by_operator"] == [
        {
            "operator_id": "operator-original",
            "eligible_attendance_count": 1,
            "recurrence_count": 1,
            "recurrence_rate": "1.00",
        }
    ]
    assert body["occurrences"][0]["recurrent_attendance_id"] == "return"

    repeated = request(
        app,
        "POST",
        "/imports/recurrence/attendances/csv",
        files={"file": ("attendances.csv", (HEADER + ROWS).encode(), "text/csv")},
    )
    assert repeated.status_code == 200
    assert repeated.json()["created_count"] == 0
    assert repeated.json()["already_existing_count"] == 3
    again = request(
        app,
        "GET",
        "/recurrence/summary?reference_month=2026-07&observed_through=2026-08-30",
    )
    assert again.json()["recurrence_count"] == 1
    engine.dispose()


def test_http_rejects_incomplete_window_and_invalid_csv(tmp_path: Path) -> None:
    app, engine = application(tmp_path)
    incomplete = request(
        app,
        "GET",
        "/recurrence/summary?reference_month=2026-07&observed_through=2026-08-29",
    )
    invalid = request(
        app,
        "POST",
        "/imports/recurrence/attendances/csv",
        files={"file": ("invalid.csv", b"wrong,header\n1,2\n", "text/csv")},
    )

    assert incomplete.status_code == 422
    assert incomplete.json() == {
        "error": {
            "code": "invalid_recurrence_filters",
            "message": "Recurrence filters are invalid",
        }
    }
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "attendance_csv_structure_error"
    engine.dispose()
