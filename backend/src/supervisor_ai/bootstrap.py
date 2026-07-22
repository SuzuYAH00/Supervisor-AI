from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import (
    Clock,
    ProcessingRunIdGenerator,
    UnitOfWork,
    UnitOfWorkFactory,
)
from supervisor_ai.application.use_cases import (
    CommercialEventPhase,
    ProcessAndPersistCommercialEventUseCase,
    ProcessCommercialEventUseCase,
)
from supervisor_ai.infrastructure.importing import (
    BatchImportProcessor,
    CsvImportAdapter,
    CsvImportService,
    JsonCommercialEventImporter,
)
from supervisor_ai.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from supervisor_ai.infrastructure.rules_engine_handlers import (
    LedgerPostingPhaseHandler,
    OperationalRulesPhaseHandler,
    PaymentValidationPhaseHandler,
    RemunerationAmountPhaseHandler,
    RemunerationEligibilityPhaseHandler,
    RulesPhaseHandler,
)
from supervisor_ai.infrastructure.runtime import (
    SystemClock,
    UuidProcessingRunIdGenerator,
)
from supervisor_ai.rules_engine import (
    AdministrativeNatureRule,
    AuthorshipConflictRule,
    CommercialAuthorRule,
    CommonAdditionalClassificationRule,
    CommonAdditionalsComparisonRule,
    CorrectiveNatureRule,
    DuplicateAuthorRule,
    ManualReviewRule,
    MeshComparisonRule,
    OperationalContextEligibilityRule,
    OperationScopeClassificationRule,
    PaymentValidationEvaluator,
    PlanChangeClassificationRule,
    PlanModalityComparisonRule,
    RecurringRevenueClassificationRule,
    RecurringValueComparisonRule,
    RemunerationAmountEvaluator,
    RemunerationEligibilityEvaluator,
    RemunerationLedgerPostingEvaluator,
    SpeedComparisonRule,
    TicketPresenceRule,
    TicketPurposeRule,
    TicketSupportRule,
)


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(create_database_engine(database_url))


def build_unit_of_work_factory(
    session_factory: sessionmaker[Session],
) -> UnitOfWorkFactory:
    def factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    return factory


def build_rules_engine() -> ProcessCommercialEventUseCase:
    return ProcessCommercialEventUseCase(
        contract_facts=RulesPhaseHandler(
            CommercialEventPhase.CONTRACT_FACTS,
            (
                SpeedComparisonRule(),
                PlanModalityComparisonRule(),
                MeshComparisonRule(),
                CommonAdditionalsComparisonRule(),
                RecurringValueComparisonRule(),
            ),
        ),
        commercial_classification=RulesPhaseHandler(
            CommercialEventPhase.COMMERCIAL_CLASSIFICATION,
            (
                PlanChangeClassificationRule(),
                RecurringRevenueClassificationRule(),
                CommonAdditionalClassificationRule(),
                OperationScopeClassificationRule(),
            ),
        ),
        operational_context=OperationalRulesPhaseHandler(
            CommercialEventPhase.OPERATIONAL_CONTEXT,
            (
                TicketPresenceRule(),
                TicketSupportRule(),
                CommercialAuthorRule(),
                DuplicateAuthorRule(),
                TicketPurposeRule(),
                AdministrativeNatureRule(),
                CorrectiveNatureRule(),
                AuthorshipConflictRule(),
                ManualReviewRule(),
                OperationalContextEligibilityRule(),
            ),
        ),
        remuneration_eligibility=RemunerationEligibilityPhaseHandler(
            RemunerationEligibilityEvaluator()
        ),
        payment_validation=PaymentValidationPhaseHandler(
            PaymentValidationEvaluator()
        ),
        remuneration_amount=RemunerationAmountPhaseHandler(
            RemunerationAmountEvaluator()
        ),
        ledger_posting=LedgerPostingPhaseHandler(
            RemunerationLedgerPostingEvaluator()
        ),
    )


def build_transactional_processor(
    database_url: str,
    *,
    clock: Clock | None = None,
    processing_run_id_generator: ProcessingRunIdGenerator | None = None,
) -> ProcessAndPersistCommercialEventUseCase:
    session_factory = build_session_factory(database_url)
    return ProcessAndPersistCommercialEventUseCase(
        processor=build_rules_engine(),
        unit_of_work_factory=build_unit_of_work_factory(session_factory),
        clock=clock or SystemClock(),
        processing_run_id_generator=(
            processing_run_id_generator or UuidProcessingRunIdGenerator()
        ),
    )


def build_json_importer(database_url: str) -> JsonCommercialEventImporter:
    return JsonCommercialEventImporter(
        processor=build_transactional_processor(database_url)
    )


def build_batch_processor(
    database_url: str,
    *,
    clock: Clock | None = None,
) -> BatchImportProcessor[str]:
    return BatchImportProcessor(
        importer=build_json_importer(database_url),
        clock=clock or SystemClock(),
    )


def build_csv_import_service(
    database_url: str,
    *,
    clock: Clock | None = None,
) -> CsvImportService:
    return CsvImportService(
        adapter=CsvImportAdapter(),
        batch_processor=build_batch_processor(database_url, clock=clock),
    )
