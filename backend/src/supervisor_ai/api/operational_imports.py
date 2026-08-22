from datetime import date
from pathlib import PurePath
from typing import Annotated, Protocol

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from supervisor_ai.api.errors import error_response
from supervisor_ai.api.schemas import ErrorResponse
from supervisor_ai.application.errors import CollaboratorExternalIdentityNotFound
from supervisor_ai.infrastructure.importing.csat_source_xlsx import (
    CsatSourceXlsxStructureError,
    CsatSourceXlsxValidationError,
)
from supervisor_ai.infrastructure.importing.employee_occurrence_xlsx import (
    EmployeeOccurrenceXlsxStructureError,
)
from supervisor_ai.infrastructure.importing.npx_workforce_xlsx import (
    NpxWorkbookStructureError,
)
from supervisor_ai.infrastructure.importing.operational_imports import (
    OperationalImportResult,
    OperationalImportType,
)
from supervisor_ai.infrastructure.importing.workforce_schedule_xlsx import (
    WorkforceScheduleXlsxError,
)


class OperationalImportContract(Protocol):
    def catalog(self): ...
    def import_file(self, import_type, filename, content, competence_month): ...


def operational_imports_router(service: OperationalImportContract) -> APIRouter:
    router = APIRouter(prefix="/operational-imports", tags=["imports"])

    @router.get("")
    async def catalog() -> dict[str, object]:
        return {
            "items": [
                {
                    "type": item.import_type.value,
                    "label": item.label,
                    "source": item.source,
                    "status": "ready" if item.ready else "not_ready",
                    "requires_competence": item.requires_competence,
                    "accepted_extensions": list(item.accepted_extensions),
                    "not_ready_reason": item.not_ready_reason,
                }
                for item in service.catalog()
            ],
            "history_available": False,
        }

    @router.post(
        "/{import_type}",
        response_model=None,
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )
    async def import_file(
        import_type: str,
        file: Annotated[UploadFile, File()],
        competence_month: Annotated[str | None, Form()] = None,
    ) -> dict[str, object] | JSONResponse:
        try:
            selected = OperationalImportType(import_type)
        except ValueError:
            return error_response(
                404, "unsupported_import_type", "Import type is not supported"
            )
        filename = PurePath(file.filename or "").name
        if not filename:
            return error_response(422, "invalid_upload", "Filename is required")
        definition = next(
            item for item in service.catalog() if item.import_type is selected
        )
        if PurePath(filename).suffix.lower() not in definition.accepted_extensions:
            return error_response(
                422,
                "unsupported_file_extension",
                "File extension is not supported for this import type",
            )
        try:
            month = (
                None
                if competence_month is None
                else date.fromisoformat(f"{competence_month}-01")
            )
        except ValueError:
            return error_response(
                422, "invalid_competence_month", "Competence month must use YYYY-MM"
            )
        content = await file.read()
        if not content:
            return error_response(422, "empty_upload", "File must not be empty")
        try:
            result = service.import_file(selected, filename, content, month)
        except NotImplementedError as error:
            return error_response(409, "import_type_not_ready", str(error))
        except CollaboratorExternalIdentityNotFound as error:
            return error_response(422, "unknown_collaborator_alias", str(error))
        except (
            CsatSourceXlsxStructureError,
            EmployeeOccurrenceXlsxStructureError,
            NpxWorkbookStructureError,
            WorkforceScheduleXlsxError,
        ):
            return error_response(
                400,
                "invalid_import_file",
                "File structure does not match the selected import type",
            )
        except CsatSourceXlsxValidationError:
            return error_response(
                422, "invalid_import_data", "File contains invalid operational data"
            )
        except ValueError as error:
            return error_response(422, "invalid_import_parameters", str(error))
        except Exception:
            return error_response(
                409, "import_conflict", "Import conflicts with persisted facts"
            )
        return _result(result)

    return router


def _result(result: OperationalImportResult) -> dict[str, object]:
    return {
        "import_type": result.import_type.value,
        "source": result.source,
        "filename": result.filename,
        "competence_month": None
        if result.competence_month is None
        else result.competence_month.strftime("%Y-%m"),
        "status": "success_with_warnings"
        if result.rejected_records or result.conflict_records
        else "success",
        "total_records": result.total_records,
        "accepted_records": result.accepted_records,
        "duplicate_records": result.duplicate_records,
        "rejected_records": result.rejected_records,
        "conflict_records": result.conflict_records,
        "unknown_aliases": sorted(
            {
                item.external_identity
                for item in result.issues
                if item.code == "unknown_collaborator_alias" and item.external_identity
            }
        ),
        "issues": [
            item.__dict__
            if hasattr(item, "__dict__")
            else {
                "code": item.code,
                "message": item.message,
                "row": item.row,
                "sheet": item.sheet,
                "field": item.field,
                "raw_value": item.raw_value,
                "external_identity": item.external_identity,
            }
            for item in result.issues
        ],
        "coverages": [
            {
                "dataset": item.dataset,
                "source": item.source,
                "covered_through": item.covered_through.isoformat(),
            }
            for item in result.coverages
        ],
        "warnings": list(result.warnings),
        "processing_run_id": result.processing_run_id,
    }
