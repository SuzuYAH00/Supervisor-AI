from enum import StrEnum


class ContractualFactName(StrEnum):
    """Identificadores estáveis dos fatos derivados na Fase A."""

    SPEED_INCREASED = "speed_increased"
    SPEED_DECREASED = "speed_decreased"
    SPEED_UNCHANGED = "speed_unchanged"
    SPEED_NOT_EVALUABLE = "speed_not_evaluable"
    SPEED_INCONSISTENT = "speed_inconsistent"

    PLAN_MODALITY_CHANGED = "plan_modality_changed"
    PLAN_MODALITY_UNCHANGED = "plan_modality_unchanged"
    PLAN_MODALITY_NOT_EVALUABLE = "plan_modality_not_evaluable"
    PLAN_MODALITY_INCONSISTENT = "plan_modality_inconsistent"

    MESH_INCLUDED = "mesh_included"
    MESH_REMOVED = "mesh_removed"
    MESH_UNCHANGED = "mesh_unchanged"
    MESH_NOT_EVALUABLE = "mesh_not_evaluable"
    MESH_INCONSISTENT = "mesh_inconsistent"

    COMMON_ADDITIONAL_INCLUDED = "common_additional_included"
    COMMON_ADDITIONAL_REMOVED = "common_additional_removed"
    COMMON_ADDITIONALS_UNCHANGED = "common_additionals_unchanged"
    COMMON_ADDITIONALS_NOT_EVALUABLE = "common_additionals_not_evaluable"
    COMMON_ADDITIONALS_INCONSISTENT = "common_additionals_inconsistent"

    RECURRING_VALUE_INCREASED = "recurring_value_increased"
    RECURRING_VALUE_DECREASED = "recurring_value_decreased"
    RECURRING_VALUE_UNCHANGED = "recurring_value_unchanged"
    RECURRING_VALUE_NOT_EVALUABLE = "recurring_value_not_evaluable"
    RECURRING_VALUE_INCONSISTENT = "recurring_value_inconsistent"


class CommercialClassificationName(StrEnum):
    """Identificadores estáveis das decisões comerciais da Fase B."""

    PLAN_CHANGED = "plan_changed"
    PLAN_UNCHANGED = "plan_unchanged"
    PLAN_CHANGE_NOT_EVALUABLE = "plan_change_not_evaluable"
    PLAN_CHANGE_INCONSISTENT = "plan_change_inconsistent"

    COMMERCIAL_UPGRADE = "commercial_upgrade"
    COMMERCIAL_DOWNGRADE = "commercial_downgrade"
    RECURRING_REVENUE_UNCHANGED = "recurring_revenue_unchanged"
    RECURRING_REVENUE_NOT_EVALUABLE = "recurring_revenue_not_evaluable"
    RECURRING_REVENUE_INCONSISTENT = "recurring_revenue_inconsistent"

    COMMON_ADDITIONAL_SALE = "common_additional_sale"
    COMMON_ADDITIONAL_REMOVAL = "common_additional_removal"
    COMMON_ADDITIONAL_CLASSIFICATION_NOT_EVALUABLE = (
        "common_additional_classification_not_evaluable"
    )
    COMMON_ADDITIONAL_CLASSIFICATION_INCONSISTENT = (
        "common_additional_classification_inconsistent"
    )

    ADDITIONAL_ONLY_OPERATION = "additional_only_operation"
    MIXED_PLAN_AND_ADDITIONAL_OPERATION = "mixed_plan_and_additional_operation"
    OPERATION_SCOPE_NOT_EVALUABLE = "operation_scope_not_evaluable"
    OPERATION_SCOPE_INCONSISTENT = "operation_scope_inconsistent"


class OperationalFactName(StrEnum):
    """Identificadores dos fatos operacionais fornecidos à Fase C."""

    TICKET_FOUND = "ticket_found"
    TICKET_NOT_FOUND = "ticket_not_found"
    TICKET_LOOKUP_NOT_EVALUABLE = "ticket_lookup_not_evaluable"
    TICKET_LOOKUP_INCONSISTENT = "ticket_lookup_inconsistent"

    TICKET_OPENED_BY_SUPPORT = "ticket_opened_by_support"
    TICKET_OPENED_OUTSIDE_SUPPORT = "ticket_opened_outside_support"
    TICKET_AREA_NOT_EVALUABLE = "ticket_area_not_evaluable"
    TICKET_AREA_INCONSISTENT = "ticket_area_inconsistent"

    TICKET_AUTHOR_IDENTIFIED = "ticket_author_identified"
    TICKET_AUTHOR_MISSING = "ticket_author_missing"
    TICKET_AUTHORSHIP_NOT_EVALUABLE = "ticket_authorship_not_evaluable"
    TICKET_AUTHORSHIP_INCONSISTENT = "ticket_authorship_inconsistent"

    EXECUTOR_IDENTIFIED = "executor_identified"
    EXECUTOR_MISSING = "executor_missing"
    EXECUTOR_NOT_EVALUABLE = "executor_not_evaluable"
    EXECUTOR_INCONSISTENT = "executor_inconsistent"

    DUPLICATE_AUTHOR_DETECTED = "duplicate_author_detected"
    DUPLICATE_AUTHOR_NOT_DETECTED = "duplicate_author_not_detected"
    DUPLICATE_AUTHOR_NOT_EVALUABLE = "duplicate_author_not_evaluable"
    DUPLICATE_AUTHOR_INCONSISTENT = "duplicate_author_inconsistent"

    TICKET_LINKED_TO_PLAN_CHANGE = "ticket_linked_to_plan_change"
    TICKET_NOT_LINKED_TO_PLAN_CHANGE = "ticket_not_linked_to_plan_change"
    TICKET_PURPOSE_NOT_EVALUABLE = "ticket_purpose_fact_not_evaluable"
    TICKET_PURPOSE_INCONSISTENT = "ticket_purpose_fact_inconsistent"

    CHANGE_MARKED_ADMINISTRATIVE = "change_marked_administrative"
    CHANGE_NOT_MARKED_ADMINISTRATIVE = "change_not_marked_administrative"
    ADMINISTRATIVE_NATURE_NOT_EVALUABLE = (
        "administrative_nature_fact_not_evaluable"
    )
    ADMINISTRATIVE_NATURE_INCONSISTENT = "administrative_nature_fact_inconsistent"

    CHANGE_MARKED_CORRECTIVE = "change_marked_corrective"
    CHANGE_NOT_MARKED_CORRECTIVE = "change_not_marked_corrective"
    CORRECTIVE_NATURE_NOT_EVALUABLE = "corrective_nature_fact_not_evaluable"
    CORRECTIVE_NATURE_INCONSISTENT = "corrective_nature_fact_inconsistent"

    CONFLICTING_AUTHORSHIP_EVIDENCE_FOUND = (
        "conflicting_authorship_evidence_found"
    )
    CONFLICTING_AUTHORSHIP_EVIDENCE_NOT_FOUND = (
        "conflicting_authorship_evidence_not_found"
    )
    AUTHORSHIP_CONFLICT_NOT_EVALUABLE = (
        "authorship_conflict_fact_not_evaluable"
    )
    AUTHORSHIP_CONFLICT_INCONSISTENT = "authorship_conflict_fact_inconsistent"


class OperationalDecisionName(StrEnum):
    """Identificadores estáveis das decisões operacionais da Fase C."""

    TICKET_PRESENT = "ticket_present"
    TICKET_MISSING = "ticket_missing"
    TICKET_PRESENCE_NOT_EVALUABLE = "ticket_presence_not_evaluable"
    TICKET_PRESENCE_INCONSISTENT = "ticket_presence_inconsistent"

    SUPPORT_TICKET = "support_ticket"
    NON_SUPPORT_TICKET = "non_support_ticket"
    TICKET_SUPPORT_NOT_EVALUABLE = "ticket_support_not_evaluable"
    TICKET_SUPPORT_INCONSISTENT = "ticket_support_inconsistent"

    COMMERCIAL_AUTHOR_IDENTIFIED = "commercial_author_identified"
    COMMERCIAL_AUTHOR_MISSING = "commercial_author_missing"
    COMMERCIAL_AUTHOR_NOT_EVALUABLE = "commercial_author_not_evaluable"
    COMMERCIAL_AUTHOR_INCONSISTENT = "commercial_author_inconsistent"

    DUPLICATE_AUTHOR = "duplicate_author"
    NO_DUPLICATE_AUTHOR = "no_duplicate_author"
    DUPLICATE_AUTHOR_NOT_EVALUABLE = "duplicate_author_not_evaluable"
    DUPLICATE_AUTHOR_INCONSISTENT = "duplicate_author_inconsistent"

    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    MANUAL_REVIEW_NOT_EVALUABLE = "manual_review_not_evaluable"
    MANUAL_REVIEW_INCONSISTENT = "manual_review_inconsistent"

    OPERATIONAL_CONTEXT_ELIGIBLE = "operational_context_eligible"
    OPERATIONAL_CONTEXT_INELIGIBLE = "operational_context_ineligible"
    OPERATIONAL_CONTEXT_NOT_EVALUABLE = "operational_context_not_evaluable"
    OPERATIONAL_CONTEXT_INCONSISTENT = "operational_context_inconsistent"

    PLAN_CHANGE_TICKET = "plan_change_ticket"
    NON_PLAN_CHANGE_TICKET = "non_plan_change_ticket"
    TICKET_PURPOSE_NOT_EVALUABLE = "ticket_purpose_not_evaluable"
    TICKET_PURPOSE_INCONSISTENT = "ticket_purpose_inconsistent"

    ADMINISTRATIVE_CHANGE = "administrative_change"
    NON_ADMINISTRATIVE_CHANGE = "non_administrative_change"
    ADMINISTRATIVE_NATURE_NOT_EVALUABLE = (
        "administrative_nature_not_evaluable"
    )
    ADMINISTRATIVE_NATURE_INCONSISTENT = "administrative_nature_inconsistent"

    CORRECTIVE_CHANGE = "corrective_change"
    NON_CORRECTIVE_CHANGE = "non_corrective_change"
    CORRECTIVE_NATURE_NOT_EVALUABLE = "corrective_nature_not_evaluable"
    CORRECTIVE_NATURE_INCONSISTENT = "corrective_nature_inconsistent"

    AUTHORSHIP_CONFLICT = "authorship_conflict"
    NO_AUTHORSHIP_CONFLICT = "no_authorship_conflict"
    AUTHORSHIP_CONFLICT_NOT_EVALUABLE = "authorship_conflict_not_evaluable"
    AUTHORSHIP_CONFLICT_INCONSISTENT = "authorship_conflict_inconsistent"
