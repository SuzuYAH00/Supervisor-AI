from supervisor_ai.processing_engine.types import ProcessedValue


class TechnicalValueNormalizer:
    """Normaliza recursivamente valores técnicos sem aplicar regras de negócio."""

    def normalize(self, value: ProcessedValue) -> ProcessedValue:
        """Reconstrói contêineres e preserva escalares que não exigem ajuste."""
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        if isinstance(value, list):
            return [self.normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: self.normalize(item) for key, item in value.items()}
        return value
