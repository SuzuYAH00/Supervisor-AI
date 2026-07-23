class ApplicationConflict(Exception):
    """Conflito esperado entre uma gravação solicitada e fatos já persistidos."""


class CommercialEventConflict(ApplicationConflict):
    """Uma referência externa já identifica outro conteúdo comercial."""


class LedgerConflict(ApplicationConflict):
    """O crédito existente diverge daquele produzido no reprocessamento."""


class CommercialEventNotFound(Exception):
    """O evento comercial solicitado não existe na persistência."""
