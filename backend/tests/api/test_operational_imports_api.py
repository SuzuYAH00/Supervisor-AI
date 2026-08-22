from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from supervisor_ai.api.operational_imports import operational_imports_router
from supervisor_ai.infrastructure.importing.operational_imports import (
    CATALOG,
    OperationalImportCoverage,
    OperationalImportResult,
    OperationalImportType,
)


class Service:
    def __init__(self) -> None:
        self.calls = []

    def catalog(self):
        return CATALOG

    def import_file(self, import_type, filename, content, competence_month):
        if import_type is OperationalImportType.RECURRENCE_MK:
            raise NotImplementedError("not ready")
        self.calls.append((import_type, filename, content, competence_month))
        return OperationalImportResult(
            import_type,
            next(item.source for item in CATALOG if item.import_type is import_type),
            filename,
            competence_month,
            2,
            1,
            1,
            0,
            0,
            coverages=(
                OperationalImportCoverage("dataset", "source", date(2026, 8, 31)),
            ),
        )


def client(service: Service) -> TestClient:
    app = FastAPI()
    app.include_router(operational_imports_router(service))
    return TestClient(app)


def test_catalog_marks_only_recurrence_as_not_ready():
    response = client(Service()).get("/operational-imports")
    assert response.status_code == 200
    states = {item["type"]: item["status"] for item in response.json()["items"]}
    assert states["recurrence_mk"] == "not_ready"
    assert sum(value == "ready" for value in states.values()) == 6
    assert response.json()["history_available"] is False


@pytest.mark.parametrize(
    ("import_type", "needs_month"),
    (
        ("workforce_schedule", True),
        ("csat_chat_mk", False),
        ("csat_phone_npx", False),
        ("npx_work_sessions", True),
        ("npx_pauses", True),
        ("employee_occurrences", False),
    ),
)
def test_endpoint_dispatches_every_ready_type(import_type, needs_month):
    service = Service()
    data = {"competence_month": "2026-08"} if needs_month else {}
    response = client(service).post(
        f"/operational-imports/{import_type}",
        data=data,
        files={"file": ("sample.xlsx", b"xlsx", "application/vnd.ms-excel")},
    )
    assert response.status_code == 200
    assert response.json()["accepted_records"] == 1
    assert response.json()["duplicate_records"] == 1
    assert response.json()["coverages"][0]["covered_through"] == "2026-08-31"
    assert service.calls[0][0] is OperationalImportType(import_type)


def test_endpoint_rejects_invalid_type_extension_and_month():
    api = client(Service())
    file = {"file": ("sample.xlsx", b"xlsx")}
    assert api.post("/operational-imports/unknown", files=file).status_code == 404
    assert (
        api.post(
            "/operational-imports/csat_chat_mk",
            files={"file": ("sample.csv", b"csv")},
        ).status_code
        == 422
    )
    assert (
        api.post(
            "/operational-imports/npx_pauses",
            data={"competence_month": "invalid"},
            files=file,
        ).status_code
        == 422
    )


def test_not_ready_type_is_explicit():
    response = client(Service()).post(
        "/operational-imports/recurrence_mk",
        data={"competence_month": "2026-08"},
        files={"file": ("sample.xlsx", b"xlsx")},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "import_type_not_ready"
