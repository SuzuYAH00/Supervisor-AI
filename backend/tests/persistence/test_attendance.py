from datetime import UTC, date, datetime

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import AttendanceFact
from supervisor_ai.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from supervisor_ai.rules_engine import ClassificationIdentity


def attendance(
    attendance_id: str,
    *,
    customer: str = "customer-1",
    operator: str = "operator-1",
    channel: str = "phone",
    occurred_at: datetime = datetime(2026, 7, 20, 12, tzinfo=UTC),
) -> AttendanceFact:
    return AttendanceFact(
        id=attendance_id,
        external_reference=f"protocol-{attendance_id}",
        source="local-export",
        customer_code=customer,
        operator_id=operator,
        channel=channel,
        occurred_at=occurred_at,
        process=ClassificationIdentity("01", "Atendimento Suporte"),
        opening_classification=ClassificationIdentity(
            "001", "Sem acesso a internet"
        ),
        closing_classification=ClassificationIdentity(
            "001", "Dispositivo Cliente"
        ),
        created_at=datetime(2026, 8, 30, 12, tzinfo=UTC),
    )


def test_repository_persists_full_factual_identity(
    session_factory: sessionmaker[Session],
) -> None:
    expected = attendance("attendance-1")
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.attendances.add(expected)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.attendances.get_by_id(expected.id) == expected
        assert unit_of_work.attendances.get_by_source_reference(
            source="local-export", external_reference="protocol-attendance-1"
        ) == expected


def test_repository_filters_and_orders_facts(
    session_factory: sessionmaker[Session],
) -> None:
    facts = (
        attendance("b", occurred_at=datetime(2026, 7, 20, 13, tzinfo=UTC)),
        attendance("a", occurred_at=datetime(2026, 7, 20, 12, tzinfo=UTC)),
        attendance(
            "other",
            customer="customer-2",
            operator="operator-2",
            channel="whatsapp",
            occurred_at=datetime(2026, 8, 1, 12, tzinfo=UTC),
        ),
    )
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        for fact in facts:
            unit_of_work.attendances.add(fact)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        result = unit_of_work.attendances.search(
            operator_id="operator-1",
            customer_code="customer-1",
            source="local-export",
            channel="phone",
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 20),
        )

    assert tuple(item.id for item in result) == ("a", "b")
