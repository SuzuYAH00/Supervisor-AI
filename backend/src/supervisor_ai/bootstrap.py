from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.api.app import HttpApplicationServices, create_http_application
from supervisor_ai.application import (
    Clock,
    ProcessingRunIdGenerator,
    UnitOfWork,
    UnitOfWorkFactory,
)
from supervisor_ai.application.use_cases import (
    CommercialEventPhase,
    GetCollaboratorFinancialTimelineUseCase,
    GetCommercialEventDetailsUseCase,
    GetFinancialSnapshotUseCase,
    GetFinancialSummaryUseCase,
    ListCommercialEventsUseCase,
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


def build_http_application(database_url: str) -> FastAPI:
    if not database_url:
        raise ValueError("database_url must not be empty")
    return create_http_application(
        HttpApplicationServices(
            csv_import=build_csv_import_service(database_url),
            financial_snapshot=build_financial_snapshot_service(database_url),
            financial_summary=build_financial_summary_service(database_url),
            commercial_event_details=build_commercial_event_details_service(
                database_url
            ),
            commercial_event_list=build_commercial_event_list_service(database_url),
            collaborator_financial_timeline=(
                build_collaborator_financial_timeline_service(database_url)
            ),
        )
    )


def build_financial_snapshot_service(
    database_url: str,
) -> GetFinancialSnapshotUseCase:
    session_factory = build_session_factory(database_url)
    return GetFinancialSnapshotUseCase(build_unit_of_work_factory(session_factory))


def build_financial_summary_service(database_url: str) -> GetFinancialSummaryUseCase:
    session_factory = build_session_factory(database_url)
    return GetFinancialSummaryUseCase(build_unit_of_work_factory(session_factory))


def build_commercial_event_details_service(
    database_url: str,
) -> GetCommercialEventDetailsUseCase:
    session_factory = build_session_factory(database_url)
    return GetCommercialEventDetailsUseCase(
        build_unit_of_work_factory(session_factory)
    )


def build_commercial_event_list_service(
    database_url: str,
) -> ListCommercialEventsUseCase:
    session_factory = build_session_factory(database_url)
    return ListCommercialEventsUseCase(build_unit_of_work_factory(session_factory))


def build_collaborator_financial_timeline_service(
    database_url: str,
) -> GetCollaboratorFinancialTimelineUseCase:
    session_factory = build_session_factory(database_url)
    return GetCollaboratorFinancialTimelineUseCase(
        build_unit_of_work_factory(session_factory)
    )
