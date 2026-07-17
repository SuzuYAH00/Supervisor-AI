from supervisor_ai.import_engine.connector import Connector
from supervisor_ai.import_engine.types import ReadResult


class ImportPipeline:
    """Orquestra a leitura na entrada do Motor de Importação.

    Persistência, transformação e aplicação de regras pertencem a etapas futuras
    posteriores a esta fronteira e não fazem parte da execução atual.
    """

    def __init__(self, connector: Connector) -> None:
        self.connector = connector

    def run(self) -> ReadResult:
        """Executa a leitura e devolve seu resultado sem interceptar erros."""
        return self.connector.read()
