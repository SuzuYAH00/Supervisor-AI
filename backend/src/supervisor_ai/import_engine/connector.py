from typing import Protocol, runtime_checkable

from supervisor_ai.import_engine.types import ReadResult


@runtime_checkable
class Connector(Protocol):
    """Contrato de leitura implementado por qualquer fonte de dados."""

    def read(self) -> ReadResult:
        """Lê dados brutos sem persistência ou transformação de domínio.

        Raises:
            SourceReadError: Quando a fonte não puder ser lida.
        """
        ...
