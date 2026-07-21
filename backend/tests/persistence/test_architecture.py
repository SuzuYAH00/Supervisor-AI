import ast
from pathlib import Path

from supervisor_ai.application import (
    EventRepository,
    LedgerRepository,
    ProcessingRunRepository,
    UnitOfWork,
)
from supervisor_ai.infrastructure.persistence.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyLedgerRepository,
    SqlAlchemyProcessingRunRepository,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)

SOURCE_ROOT = Path(__file__).parents[2] / "src/supervisor_ai"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.module or alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }


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
                assert all("mk" not in name.lower() for name in imports)


def test_concrete_repositories_and_uow_implement_application_protocols() -> None:
    assert isinstance(SqlAlchemyEventRepository, type)
    assert isinstance(SqlAlchemyLedgerRepository, type)
    assert isinstance(SqlAlchemyProcessingRunRepository, type)
    assert isinstance(SqlAlchemyUnitOfWork, type)
    assert EventRepository is not SqlAlchemyEventRepository
    assert LedgerRepository is not SqlAlchemyLedgerRepository
    assert ProcessingRunRepository is not SqlAlchemyProcessingRunRepository
    assert UnitOfWork is not SqlAlchemyUnitOfWork


def test_persistence_scope_does_not_import_fastapi_csv_or_mk() -> None:
    directory = SOURCE_ROOT / "infrastructure/persistence"
    for path in directory.rglob("*.py"):
        imports = imported_modules(path)
        assert all("fastapi" not in name for name in imports)
        assert all(name != "csv" for name in imports)
        assert all("mk" not in name.lower() for name in imports)
