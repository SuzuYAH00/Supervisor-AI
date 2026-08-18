class ApplicationConflict(Exception):
    """Conflito esperado entre uma gravação solicitada e fatos já persistidos."""


class CommercialEventConflict(ApplicationConflict):
    """Uma referência externa já identifica outro conteúdo comercial."""


class LedgerConflict(ApplicationConflict):
    """O crédito existente diverge daquele produzido no reprocessamento."""


class CsatEvaluationConflict(ApplicationConflict):
    """A identidade da avaliação CSAT diverge dos fatos persistidos."""


class CsatContactConflict(ApplicationConflict):
    """A identidade do contato CSAT diverge dos fatos persistidos."""


class AttendanceFactConflict(ApplicationConflict):
    """A identidade do atendimento diverge dos fatos persistidos."""


class DailyWorkStatusConflict(ApplicationConflict):
    """A mesma origem ou dia de trabalho diverge do fato persistido."""


class OperationalCollaboratorProfileConflict(ApplicationConflict):
    """O perfil existente possui outra modalidade competitiva."""


class CollaboratorExternalIdentityConflict(ApplicationConflict):
    """A identidade externa já aponta para outro colaborador."""


class OperationalCollaboratorProfileNotFound(Exception):
    """O perfil canônico necessário para a associação não existe."""


class CollaboratorExternalIdentityNotFound(Exception):
    """A identidade externa não possui associação canônica."""


class CommercialEventNotFound(Exception):
    """O evento comercial solicitado não existe na persistência."""


class ProcessingRunNotFound(Exception):
    """A execução de processamento solicitada não existe na persistência."""
