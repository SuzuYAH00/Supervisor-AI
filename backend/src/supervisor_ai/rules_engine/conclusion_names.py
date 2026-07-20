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
