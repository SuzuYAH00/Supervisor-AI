import asyncio
from datetime import UTC, date, datetime
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from supervisor_ai.application import (
    CollaboratorExternalIdentity,
    OperationalCollaboratorProfile,
)
from supervisor_ai.application.use_cases import (
    DailyPlannedWorkScheduleInput,
    ImportWorkSchedulesCommand,
    ImportWorkSchedulesUseCase,
)
from supervisor_ai.bootstrap import (
    build_http_application,
    build_session_factory,
    build_unit_of_work_factory,
)
from supervisor_ai.database.base import Base
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel

NOW = datetime(2026, 8, 20, 12, tzinfo=UTC)


def test_http_lists_pending_creates_override_and_rejects_conflict(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'schedules.sqlite3'}"
    session_factory = build_session_factory(database_url)
    Base.metadata.create_all(session_factory.kw["bind"])
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.operational_collaborators.add(
            OperationalCollaboratorProfile(
                "operator-1", CsatCompetitiveChannel.CHAT, NOW
            )
        )
        uow.collaborator_external_identities.add(
            CollaboratorExternalIdentity(
                "operator-1", "attendance_sheet", "Operator One", NOW
            )
        )
        uow.commit()
    factory = build_unit_of_work_factory(session_factory)
    ImportWorkSchedulesUseCase(factory, lambda: NOW).execute(
        ImportWorkSchedulesCommand(
            daily_schedules=(
                DailyPlannedWorkScheduleInput(
                    "Operator One",
                    date(2026, 8, 20),
                    None,
                    None,
                    "unresolved",
                    "attendance_sheet",
                    "august:D20",
                    "AUGUST",
                    "D20",
                    "explicit_schedule_not_found",
                ),
            )
        )
    )
    app = build_http_application(database_url)

    async def exercise() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            pending = await client.get(
                "/work-schedules?competence_month=2026-08&resolution_status=pending"
            )
            assert pending.status_code == 200
            assert pending.json()["pending_count"] == 1
            payload = {
                "collaborator_id": "operator-1",
                "work_date": "2026-08-20",
                "planned_start": "16:00",
                "planned_end": "22:00",
                "reason": "authorized exchange",
            }
            created = await client.post("/work-schedules/overrides", json=payload)
            assert created.status_code == 201
            assert created.json()["created_by"] == "mvp-supervisor"
            conflict = await client.post(
                "/work-schedules/overrides",
                json={**payload, "planned_start": "08:00", "planned_end": "14:00"},
            )
            assert conflict.status_code == 409
            resolved = await client.get(
                "/work-schedules?competence_month=2026-08&resolution_status=with_override"
            )
            assert (
                resolved.json()["items"][0]["resolution_status"] == "resolved_override"
            )

    asyncio.run(exercise())
