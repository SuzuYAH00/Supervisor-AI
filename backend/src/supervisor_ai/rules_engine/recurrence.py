from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

RECURRENCE_WINDOW_DAYS = 30


@dataclass(frozen=True, slots=True, order=True)
class ClassificationIdentity:
    code: str | None
    description: str

    def __post_init__(self) -> None:
        if self.code is not None and not self.code.strip():
            raise ValueError("classification code must not be blank")
        if not self.description.strip():
            raise ValueError("classification description must not be blank")


@dataclass(frozen=True, slots=True)
class RecurrenceAttendance:
    attendance_id: str
    customer_code: str
    operator_id: str
    channel: str
    occurred_at: datetime
    process: ClassificationIdentity
    opening_classification: ClassificationIdentity
    closing_classification: ClassificationIdentity

    def __post_init__(self) -> None:
        for value, name in (
            (self.attendance_id, "attendance_id"),
            (self.customer_code, "customer_code"),
            (self.operator_id, "operator_id"),
            (self.channel, "channel"),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class RecurrenceOccurrence:
    original_attendance_id: str
    recurrent_attendance_id: str
    customer_code: str
    attributed_operator_id: str
    original_date: date
    recurrent_date: date
    days_between: int


ELIGIBLE_PROCESS = ClassificationIdentity("01", "Atendimento Suporte")

ELIGIBLE_OPENING_CLASSIFICATIONS = frozenset(
    {
        ClassificationIdentity("001", "Sem acesso a internet"),
        ClassificationIdentity("002", "Lentidão"),
        ClassificationIdentity("003", "Alteração de Senha/SSID"),
        ClassificationIdentity("004", "Problemas na TV"),
        ClassificationIdentity("005", "Problemas em VPN"),
        ClassificationIdentity("006", "Problemas em Jogos"),
        ClassificationIdentity("007", "Problemas Impressora"),
        ClassificationIdentity("008", "Problemas no IPTV"),
        ClassificationIdentity("009", "Problemas no WiFi"),
        ClassificationIdentity("010", "Analise de Quedas PPPoE"),
        ClassificationIdentity("011", "Velocidade do Plano"),
        ClassificationIdentity("012", "Entrga/Config. Roteador"),
        ClassificationIdentity("013", "Quedas de conexão"),
        ClassificationIdentity("014", "Mudança de Endereço"),
        ClassificationIdentity("015", "Mudança de Ponto"),
        ClassificationIdentity("016", "Melhoria de sinal"),
        ClassificationIdentity("017", "Entrega de Cabo"),
        ClassificationIdentity("018", "Aplicativo LINKCE"),
        ClassificationIdentity("019", "Sugestão/Reclamação"),
        ClassificationIdentity("020", "Linkvideo"),
        ClassificationIdentity("021", "Solicitação Boleto/Pix"),
        ClassificationIdentity("024", "Relatório de Conexão"),
        ClassificationIdentity("030", "Alteração de plano"),
        ClassificationIdentity("030", "Link PG Cartão"),
        ClassificationIdentity("106", "Pesquisa Satisfação"),
        ClassificationIdentity(None, "NPS Detratores"),
        ClassificationIdentity(None, "NPS Passivos"),
        ClassificationIdentity(None, "NPS Promotores"),
        ClassificationIdentity(None, "Dúvidas"),
    }
)

ELIGIBLE_CLOSING_CLASSIFICATIONS = frozenset(
    {
        ClassificationIdentity("001", "Dispositivo Cliente"),
        ClassificationIdentity("002", "Fonte do equipamento"),
        ClassificationIdentity("003", "Alcance do Wi-Fi"),
        ClassificationIdentity("004", "Problema no Roteador/ONT"),
        ClassificationIdentity("010", "Orientação Redes 2G/5G"),
        ClassificationIdentity("011", "Orientação Sobrecarga"),
        ClassificationIdentity("012", "Orientação Cabeamento"),
        ClassificationIdentity("013", "Orientação Velocidade"),
        ClassificationIdentity("019", "Dúvidas Linkvideo"),
        ClassificationIdentity("020", "Alteração SSID/Senha"),
        ClassificationIdentity("021", "Alteração Criptografia"),
        ClassificationIdentity("022", "Alteração de Tecnologia"),
        ClassificationIdentity("023", "Habilitar/Desab WPS"),
        ClassificationIdentity("024", "Habilitar/Desab IPv6"),
        ClassificationIdentity("025", "Config. Redirecionamento"),
        ClassificationIdentity("026", "Config. DMZ"),
        ClassificationIdentity("028", "Reprovisionamento"),
        ClassificationIdentity("029", "Roteador Reiniciado"),
        ClassificationIdentity("030", "Rota"),
        ClassificationIdentity("031", "Falha no link"),
        ClassificationIdentity("032", "Rede Interna Cliente"),
        ClassificationIdentity("033", "Elétrica do Cliente"),
        ClassificationIdentity("034", "Aplicação de Terceiros"),
        ClassificationIdentity("035", "Internet compartilhada"),
        ClassificationIdentity("036", "Roteador Resetado"),
        ClassificationIdentity("041", "Problema Conector RJ45"),
        ClassificationIdentity("002", "Internet compartilhada"),
        ClassificationIdentity("009", "Aplicação de Terceiros"),
        ClassificationIdentity("010", "Rota"),
        ClassificationIdentity("012", "Fonte do equipamento"),
        ClassificationIdentity("013", "Elétrica do Cliente"),
        ClassificationIdentity("015", "Config. Roteador"),
        ClassificationIdentity("016", "Roteador Resetado"),
        ClassificationIdentity("014", "Rede Interna Cliente"),
        ClassificationIdentity("023", "Instalação 2° Roteador"),
        ClassificationIdentity("033", "Problema Conector RJ45"),
        ClassificationIdentity("039", "Desligou equipamento"),
        ClassificationIdentity("045", "Perda de Pacote"),
    }
)


def is_recurrence_eligible(attendance: RecurrenceAttendance) -> bool:
    return all(
        (
            attendance.process == ELIGIBLE_PROCESS,
            attendance.opening_classification
            in ELIGIBLE_OPENING_CLASSIFICATIONS,
            attendance.closing_classification
            in ELIGIBLE_CLOSING_CLASSIFICATIONS,
        )
    )


def find_recurrences(
    attendances: tuple[RecurrenceAttendance, ...],
    *,
    cohort_start: date,
    cohort_end: date,
) -> tuple[RecurrenceOccurrence, ...]:
    if cohort_start > cohort_end:
        raise ValueError("cohort_start must not be after cohort_end")
    eligible = sorted(
        (item for item in attendances if is_recurrence_eligible(item)),
        key=lambda item: (
            item.customer_code,
            item.occurred_at,
            item.attendance_id,
        ),
    )
    by_customer: dict[str, list[RecurrenceAttendance]] = {}
    for attendance in eligible:
        by_customer.setdefault(attendance.customer_code, []).append(attendance)

    occurrences: list[RecurrenceOccurrence] = []
    for customer_attendances in by_customer.values():
        for original, recurrent in zip(
            customer_attendances, customer_attendances[1:], strict=False
        ):
            original_date = original.occurred_at.date()
            if not cohort_start <= original_date <= cohort_end:
                continue
            recurrent_date = recurrent.occurred_at.date()
            days_between = (recurrent_date - original_date).days
            if 0 <= days_between <= RECURRENCE_WINDOW_DAYS:
                occurrences.append(
                    RecurrenceOccurrence(
                        original_attendance_id=original.attendance_id,
                        recurrent_attendance_id=recurrent.attendance_id,
                        customer_code=original.customer_code,
                        attributed_operator_id=original.operator_id,
                        original_date=original_date,
                        recurrent_date=recurrent_date,
                        days_between=days_between,
                    )
                )
    return tuple(occurrences)


def recurrence_rate(
    recurrence_count: int, eligible_attendance_count: int
) -> Decimal | None:
    if recurrence_count < 0 or eligible_attendance_count < 0:
        raise ValueError("counts must not be negative")
    if recurrence_count > eligible_attendance_count:
        raise ValueError("recurrence count must not exceed eligible attendance count")
    if eligible_attendance_count == 0:
        return None
    return Decimal(recurrence_count) / Decimal(eligible_attendance_count)
