"""Cálculo de prazos de SLA (acordo de nível de serviço).

Horário de expediente: dias úteis (segunda a sexta), das 08:00 às 17:00.
A prioridade crítica conta em horas corridas; as restantes em horas úteis.
Feriados ainda não são considerados.
"""

from datetime import datetime, timedelta

HORA_INICIO = 8
HORA_FIM = 17

# prioridade: (horas até 1.ª resposta, horas até resolução, conta só horas úteis)
SLA = {
    "critica": (0.5, 4, False),
    "alta": (2, 8, True),
    "media": (4, 18, True),   # 18 h úteis = 2 dias úteis
    "baixa": (9, 45, True),   # 45 h úteis = 5 dias úteis
}


def _para_expediente(t: datetime) -> datetime:
    while True:
        if t.weekday() >= 5 or t.hour >= HORA_FIM:
            t = (t + timedelta(days=1)).replace(hour=HORA_INICIO, minute=0, second=0, microsecond=0)
            continue
        if t.hour < HORA_INICIO:
            t = t.replace(hour=HORA_INICIO, minute=0, second=0, microsecond=0)
        return t


def somar_horas_uteis(inicio: datetime, horas: float) -> datetime:
    restante = timedelta(hours=horas)
    t = inicio
    while True:
        t = _para_expediente(t)
        fim_dia = t.replace(hour=HORA_FIM, minute=0, second=0, microsecond=0)
        disponivel = fim_dia - t
        if restante <= disponivel:
            return t + restante
        restante -= disponivel
        t = fim_dia


def prazos(prioridade: str, inicio: datetime) -> tuple[datetime, datetime]:
    resp, resol, uteis = SLA[prioridade]
    if uteis:
        return somar_horas_uteis(inicio, resp), somar_horas_uteis(inicio, resol)
    return inicio + timedelta(hours=resp), inicio + timedelta(hours=resol)


def estado_sla(p, agora: datetime) -> str:
    """ok | em_risco | violado | cumprido | pausado | n/a"""
    if p.estado in ("recusado", "cancelado"):
        return "n/a"
    if p.estado == "em_aprovacao":
        return "pausado"
    if p.resolvido_em is not None:
        return "cumprido" if p.resolvido_em <= p.prazo_resolucao else "violado"
    if agora > p.prazo_resolucao:
        return "violado"
    total = (p.prazo_resolucao - p.sla_inicio).total_seconds() or 1
    decorrido = (agora - p.sla_inicio).total_seconds()
    return "em_risco" if decorrido / total >= 0.75 else "ok"
