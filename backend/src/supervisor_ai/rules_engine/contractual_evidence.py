from enum import StrEnum


class ContractualEvidenceName(StrEnum):
    """Nomes estáveis das evidências consumidas pelas regras contratuais."""

    PREVIOUS_SPEED = "previous_speed"
    CURRENT_SPEED = "current_speed"
    PREVIOUS_PLAN_MODALITY = "previous_plan_modality"
    CURRENT_PLAN_MODALITY = "current_plan_modality"
    PREVIOUS_MESH_ENABLED = "previous_mesh_enabled"
    CURRENT_MESH_ENABLED = "current_mesh_enabled"
    PREVIOUS_ADDITIONALS = "previous_additionals"
    CURRENT_ADDITIONALS = "current_additionals"
    PREVIOUS_RECURRING_VALUE = "previous_recurring_value"
    CURRENT_RECURRING_VALUE = "current_recurring_value"
