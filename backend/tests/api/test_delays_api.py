import asyncio
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from supervisor_ai.application import (
    CollaboratorExternalIdentity,
    OperationalCollaboratorProfile,
)
from supervisor_ai.application.use_cases import (
    GetMonthlyDelayCountQuery,
    ImportNpxFactsCommand,
    ImportNpxFactsUseCase,
    PauseInput,
)
from supervisor_ai.bootstrap import (
    build_http_application,
    build_monthly_delay_count_service,
    build_session_factory,
    build_unit_of_work_factory,
)
from supervisor_ai.database.base import Base
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel

NOW = datetime(2026, 8, 18, 12, tzinfo=UTC)


def test_review_api_changes_monthly_count_without_changing_npx_fact(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'delays.sqlite3'}"
    session_factory = build_session_factory(database_url)
    Base.metadata.create_all(session_factory.kw["bind"])
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.operational_collaborators.add(
            OperationalCollaboratorProfile(
                "operator-1", CsatCompetitiveChannel.CHAT, NOW
            )
        )
        uow.collaborator_external_identities.add(
            CollaboratorExternalIdentity("operator-1", "npx", "Agent Test", NOW)
        )
        uow.commit()
    start = datetime(2026, 8, 3, 10, tzinfo=UTC)
    ImportNpxFactsUseCase(
        build_unit_of_work_factory(session_factory), lambda: NOW
    ).execute(
        ImportNpxFactsCommand(
            pauses=(
                PauseInput(
                    "pause-api",
                    "pause-api-ref",
                    "Agent Test",
                    "001",
                    "Support",
                    start,
                    start + timedelta(minutes=21),
                    1260,
                    "extract",
                    "Sheet1",
                    2,
                    "Intervalo 20min",
                    None,
                ),
            )
        )
    )
    app = build_http_application(database_url)

    async def exercise() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            listing = await client.get("/delays?competence_month=2026-08")
            assert listing.status_code == 200
            body = listing.json()
            assert body["pending_count"] == 1
            occurrence_id = body["items"][0]["delay_occurrence_id"]
            reviewed = await client.post(
                f"/delays/{occurrence_id}/reviews",
                json={"decision": "corrected", "note": "Reviewed manually"},
            )
            assert reviewed.status_code == 201
            assert reviewed.json()["decided_by"] == "mvp-supervisor"
            corrected = await client.get(
                "/delays?competence_month=2026-08&review_status=corrected"
            )
            assert corrected.json()["corrected_count"] == 1
            assert corrected.json()["items"][0]["counts_for_rv"] is False

    asyncio.run(exercise())
    count = build_monthly_delay_count_service(database_url).execute(
        GetMonthlyDelayCountQuery("operator-1", date(2026, 8, 1))
    )
    assert count.delay_count == 0
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.pauses.get_by_id("pause-api").duration_seconds == 1260
