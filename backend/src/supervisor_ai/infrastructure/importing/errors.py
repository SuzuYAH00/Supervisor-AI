class ImportDocumentError(Exception):
    """Base dos erros pertencentes ao transporte do documento de entrada."""


class JsonSyntaxError(ImportDocumentError):
    """O texto não representa um documento JSON estrito."""


class ImportValidationError(ImportDocumentError):
    """O JSON é sintaticamente válido, mas viola o schema de importação."""
