import ast
from pathlib import Path

from supervisor_ai.application import (
    AttendanceRepository,
    CsatRepository,
    DailyWorkStatusRepository,
    EventRepository,
    LedgerRepository,
    OperationalCollaboratorProfileRepository,
    ProcessingRunRepository,
    UnitOfWork,
)
from supervisor_ai.infrastructure.persistence.repositories import (
    SqlAlchemyAttendanceRepository,
    SqlAlchemyCsatRepository,
    SqlAlchemyDailyWorkStatusRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyLedgerRepository,
    SqlAlchemyOperationalCollaboratorProfileRepository,
    SqlAlchemyProcessingRunRepository,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)

SOURCE_ROOT = Path(__file__).parents[2] / "src/supervisor_ai"
MK_OPERATIONAL_IMPORTS = {
    "resolve_mk_operator_identities",
    "supervisor_ai.application.mk_operational",
    "supervisor_ai.infrastructure.persistence.mk_operational",
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
    return modules


def test_rules_engine_and_application_do_not_import_orm() -> None:
    for directory in (SOURCE_ROOT / "rules_engine", SOURCE_ROOT / "application"):
        for path in directory.rglob("*.py"):
            imports = imported_modules(path)
            assert all("sqlalchemy" not in name for name in imports)
            assert all(
                "infrastructure.persistence.models" not in name for name in imports
            )
            if directory.name == "application":
                assert all("infrastructure" not in name for name in imports)
                assert all("fastapi" not in name for name in imports)
                assert all(name != "csv" for name in imports)
                assert all(
                    "mk" not in name.lower() or name in MK_OPERATIONAL_IMPORTS
                    for name in imports
                )


def test_concrete_repositories_and_uow_implement_application_protocols() -> None:
    assert isinstance(SqlAlchemyEventRepository, type)
    assert isinstance(SqlAlchemyAttendanceRepository, type)
    assert isinstance(SqlAlchemyCsatRepository, type)
    assert isinstance(SqlAlchemyDailyWorkStatusRepository, type)
    assert isinstance(SqlAlchemyLedgerRepository, type)
    assert isinstance(SqlAlchemyOperationalCollaboratorProfileRepository, type)
    assert isinstance(SqlAlchemyProcessingRunRepository, type)
    assert isinstance(SqlAlchemyUnitOfWork, type)
    assert EventRepository is not SqlAlchemyEventRepository
    assert AttendanceRepository is not SqlAlchemyAttendanceRepository
    assert CsatRepository is not SqlAlchemyCsatRepository
    assert DailyWorkStatusRepository is not SqlAlchemyDailyWorkStatusRepository
    assert LedgerRepository is not SqlAlchemyLedgerRepository
    assert (
        OperationalCollaboratorProfileRepository
        is not SqlAlchemyOperationalCollaboratorProfileRepository
    )
    assert ProcessingRunRepository is not SqlAlchemyProcessingRunRepository
    assert UnitOfWork is not SqlAlchemyUnitOfWork


def test_persistence_scope_only_imports_approved_mk_operational_contract() -> None:
    directory = SOURCE_ROOT / "infrastructure/persistence"
    for path in directory.rglob("*.py"):
        imports = imported_modules(path)
        assert all("fastapi" not in name for name in imports)
        assert all(name != "csv" for name in imports)
        assert all(
            "mk" not in name.lower() or name in MK_OPERATIONAL_IMPORTS
            for name in imports
        )
