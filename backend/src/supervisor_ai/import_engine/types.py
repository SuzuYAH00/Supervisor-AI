from dataclasses import dataclass, field
from datetime import datetime

type RawScalar = str | int | float | bool | None
type RawValue = RawScalar | list[RawValue] | dict[str, RawValue]


@dataclass(slots=True)
class RawRecord:
    """Registro bruto mutável, preservado no formato entregue pela fonte.

    ``metadata`` contém apenas contexto técnico deste registro, separado do
    conteúdo original armazenado em ``data``.
    """

    data: dict[str, RawValue]
    external_id: str | None = None
    metadata: dict[str, RawValue] = field(default_factory=dict)


@dataclass(slots=True)
class SourceMetadata:
    """Contexto técnico mutável de uma leitura, independente do fornecedor."""

    source_name: str
    read_at: datetime
    cursor: str | None = None
    attributes: dict[str, RawValue] = field(default_factory=dict)


@dataclass(slots=True)
class ReadResult:
    """Resultado mutável produzido por uma leitura concluída.

    Os contêineres permanecem mutáveis para preservar as estruturas nativas dos
    dados brutos. Consumidores que precisem de snapshots devem copiá-los.
    """

    records: list[RawRecord]
    metadata: SourceMetadata


class SourceReadError(Exception):
    """Falha ao ler registros de uma fonte externa."""

    def __init__(
        self,
        source_name: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.source_name = source_name
        self.message = message
        self.retryable = retryable

    def __str__(self) -> str:
        return f"{self.source_name}: {self.message}"
