from datetime import date, datetime
from decimal import Decimal

from supervisor_ai.infrastructure.external.mk.contracts import (
    MK_CONTRACT_OPERATION_DOWNGRADE,
    MK_CONTRACT_OPERATION_UPGRADE,
)
from supervisor_ai.infrastructure.external.mk.queries import (
    MkContractOperationRepository,
    MkContractPlanChangeRepository,
    MkContractRepository,
    MkPlanRepository,
)
from tests.infrastructure.test_mk_queries import FakeEngine


def test_contract_and_plan_queries_preserve_stable_source_identities() -> None:
    contract_engine = FakeEngine(
        [
            {
                "contract_id": 91,
                "customer_id": 52,
                "current_plan_id": 8,
                "cancelado": "N",
                "suspenso": "N",
                "joined_on": date(2020, 1, 2),
                "activated_at": datetime(2020, 1, 3, 10),
            }
        ]
    )
    plan_engine = FakeEngine(
        [
            {
                "plan_id": 8,
                "descricao": "Plano factual",
                "vlr_mensalidade": "99.90",
                "download_speed": 500,
                "upload_speed": 250,
                "velocidades_formatadas": "500/250",
            }
        ]
    )

    contract = MkContractRepository(contract_engine).list_page(after_id=90)[0]  # type: ignore[arg-type]
    plan = MkPlanRepository(plan_engine).list_page(after_id=7)[0]  # type: ignore[arg-type]

    assert (contract.contract_id, contract.customer_id, contract.current_plan_id) == (
        91,
        52,
        8,
    )
    assert (plan.plan_id, plan.monthly_value) == (8, Decimal("99.90"))
    for engine in (contract_engine, plan_engine):
        sql, _ = engine.connection.calls[0]
        assert "SELECT *" not in sql.upper()
        assert "OFFSET" not in sql.upper()
        assert "ORDER BY" in sql.upper()


def test_plan_change_query_preserves_nulls_unknown_operations_and_a_b_c() -> None:
    rows = [
        {
            "plan_change_id": 100,
            "contract_id": 91,
            "operation_code": 4,
            "old_plan_id": 7,
            "new_plan_id": 8,
            "changed_at": datetime(2025, 1, 1, 9),
            "changed_by_login": "operator",
            "changed_by_user_id": 31,
            "value_delta": "20.00",
            "extra_context": None,
        },
        {
            "plan_change_id": 101,
            "contract_id": 91,
            "operation_code": 5,
            "old_plan_id": 8,
            "new_plan_id": 9,
            "changed_at": datetime(2025, 2, 1, 9),
            "changed_by_login": "legacy",
            "changed_by_user_id": None,
            "value_delta": None,
            "extra_context": "factual",
        },
        {
            "plan_change_id": 102,
            "contract_id": 92,
            "operation_code": 99,
            "old_plan_id": None,
            "new_plan_id": None,
            "changed_at": datetime(2025, 3, 1, 9),
            "changed_by_login": "unknown",
            "changed_by_user_id": None,
            "value_delta": None,
            "extra_context": None,
        },
    ]
    engine = FakeEngine(rows)

    changes = MkContractPlanChangeRepository(engine).list_page(after_id=99)  # type: ignore[arg-type]

    assert [
        (item.plan_change_id, item.old_plan_id, item.new_plan_id)
        for item in changes[:2]
    ] == [(100, 7, 8), (101, 8, 9)]
    assert changes[1].changed_by_user_id is None
    assert changes[2].operation_code == 99
    assert changes[2].old_plan_id is changes[2].new_plan_id is None
    sql, parameters = engine.connection.calls[0]
    assert "codcontratohist > :after_id" in sql
    assert "HAVING count(*) = 1" in sql
    assert parameters["after_id"] == 99


def test_operation_catalog_centralizes_known_codes_and_preserves_raw_catalog() -> None:
    engine = FakeEngine(
        [
            {"operation_code": 4, "description": "Upgrade"},
            {"operation_code": 5, "description": "Downgrade"},
            {"operation_code": 99, "description": "Outra"},
        ]
    )
    operations = MkContractOperationRepository(engine).load()  # type: ignore[arg-type]
    assert MK_CONTRACT_OPERATION_UPGRADE == operations[0].operation_code == 4
    assert MK_CONTRACT_OPERATION_DOWNGRADE == operations[1].operation_code == 5
    assert operations[2].operation_code == 99
