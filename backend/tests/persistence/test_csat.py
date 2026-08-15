from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import CsatEvaluation
from supervisor_ai.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


def evaluation(
    evaluation_id: str,
    *,
    collaborator_id: str = "collaborator-1",
    channel: str | None = "whatsapp",
    source: str = "mkbot-export",
    score: str = "10",
    evaluated_at: datetime = datetime(2026, 7, 20, 12, tzinfo=UTC),
) -> CsatEvaluation:
    return CsatEvaluation(
        id=evaluation_id,
        external_reference=f"external-{evaluation_id}",
        source=source,
        collaborator_id=collaborator_id,
        channel=channel,
        score=Decimal(score),
        evaluated_at=evaluated_at,
        created_at=datetime(2026, 7, 20, 13, tzinfo=UTC),
    )


def test_repository_persists_and_gets_by_both_identities(
    session_factory: sessionmaker[Session],
) -> None:
    expected = evaluation("csat-1")
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.csat.add(expected)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.csat.get_by_id("csat-1") == expected
        assert unit_of_work.csat.get_by_source_reference(
            source="mkbot-export", external_reference="external-csat-1"
        ) == expected
        assert unit_of_work.csat.get_by_id("missing") is None


def test_repository_filters_order_and_summary_are_factual(
    session_factory: sessionmaker[Session],
) -> None:
    values = (
        evaluation("csat-2", score="8", channel="whatsapp"),
        evaluation(
            "csat-1",
            score="10",
            channel="phone",
            evaluated_at=datetime(2026, 7, 19, 12, tzinfo=UTC),
        ),
        evaluation(
            "csat-3",
            collaborator_id="collaborator-2",
            score="6",
            source="npx-export",
            channel=None,
            evaluated_at=datetime(2026, 8, 1, 12, tzinfo=UTC),
        ),
    )
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        for item in values:
            unit_of_work.csat.add(item)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        filtered = unit_of_work.csat.search(
            collaborator_id="collaborator-1",
            start_date=date(2026, 7, 19),
            end_date=date(2026, 7, 20),
            source="mkbot-export",
            channel=None,
        )
        summary = unit_of_work.csat.summarize(
            collaborator_id=None,
            start_date=None,
            end_date=None,
            source=None,
            channel=None,
        )

    assert tuple(item.id for item in filtered) == ("csat-1", "csat-2")
    assert summary.evaluation_count == 3
    assert summary.score_total == Decimal("24")
    collaborator_groups = [
        (item.value, item.evaluation_count, item.score_total)
        for item in summary.by_collaborator
    ]
    assert collaborator_groups == [
        ("collaborator-1", 2, Decimal("18")),
        ("collaborator-2", 1, Decimal("6")),
    ]
    assert [(item.value, item.evaluation_count) for item in summary.by_channel] == [
        (None, 1),
        ("phone", 1),
        ("whatsapp", 1),
    ]
