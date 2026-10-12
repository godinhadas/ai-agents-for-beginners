"""Regras de negócio partilhadas pela API e pelo agente IA."""

from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .models import Actividade, Apolice, Cliente, Oportunidade, Sinistro

SINISTRO_ABERTO = ("participado", "em_analise", "aprovado")
FASES_ABERTAS = ("prospeccao", "proposta", "negociacao")


def _apolice_dict(a: Apolice) -> dict:
    return {
        "id": a.id, "numero": a.numero, "ramo": a.ramo, "estado": a.estado,
        "premio_anual": a.premio_anual, "data_fim": a.data_fim.isoformat(),
        "cliente_id": a.cliente_id, "cliente": a.cliente.nome,
    }


def pesquisar_clientes(db: Session, texto: str, limite: int = 10) -> list[dict]:
    padrao = f"%{texto.strip()}%"
    rows = db.scalars(
        select(Cliente)
        .where(or_(Cliente.nome.ilike(padrao), Cliente.nif.ilike(padrao), Cliente.email.ilike(padrao)))
        .order_by(Cliente.nome)
        .limit(limite)
    )
    return [
        {"id": c.id, "nome": c.nome, "nif": c.nif, "tipo": c.tipo, "provincia": c.provincia}
        for c in rows
    ]


def renovacoes(db: Session, dias: int = 60) -> list[dict]:
    hoje = date.today()
    rows = db.scalars(
        select(Apolice)
        .where(Apolice.estado == "activa", Apolice.data_fim.between(hoje, hoje + timedelta(days=dias)))
        .order_by(Apolice.data_fim)
    )
    return [{**_apolice_dict(a), "dias_restantes": (a.data_fim - hoje).days} for a in rows]


def sinistros_abertos(db: Session) -> list[dict]:
    rows = db.scalars(
        select(Sinistro).where(Sinistro.estado.in_(SINISTRO_ABERTO)).order_by(Sinistro.data_ocorrencia)
    )
    hoje = date.today()
    return [
        {
            "id": s.id, "numero": s.numero, "estado": s.estado,
            "apolice": s.apolice.numero, "cliente": s.apolice.cliente.nome,
            "valor_reclamado": s.valor_reclamado,
            "dias_em_aberto": (hoje - s.data_ocorrencia).days,
        }
        for s in rows
    ]


def pipeline(db: Session) -> list[dict]:
    rows = db.execute(
        select(Oportunidade.fase, func.count(), func.coalesce(func.sum(Oportunidade.valor_estimado), 0))
        .group_by(Oportunidade.fase)
    ).all()
    por_fase = {fase: (n, total) for fase, n, total in rows}
    ordem = ("prospeccao", "proposta", "negociacao", "ganha", "perdida")
    return [
        {"fase": f, "quantidade": por_fase.get(f, (0, 0))[0], "valor": float(por_fase.get(f, (0, 0))[1])}
        for f in ordem
    ]


def visao_cliente(db: Session, cliente_id: int) -> dict | None:
    c = db.get(Cliente, cliente_id)
    if c is None:
        return None
    apolices = sorted(c.apolices, key=lambda a: a.data_fim)
    sinistros = [s for a in c.apolices for s in a.sinistros]
    return {
        "cliente": {
            "id": c.id, "nome": c.nome, "tipo": c.tipo, "nif": c.nif, "email": c.email,
            "telefone": c.telefone, "provincia": c.provincia,
            "mediador": c.mediador.nome if c.mediador else None,
        },
        "premio_total_activo": sum(a.premio_anual for a in apolices if a.estado == "activa"),
        "apolices": [_apolice_dict(a) for a in apolices],
        "sinistros": [
            {"id": s.id, "numero": s.numero, "estado": s.estado, "apolice": s.apolice.numero,
             "data_ocorrencia": s.data_ocorrencia.isoformat(), "valor_reclamado": s.valor_reclamado,
             "valor_pago": s.valor_pago}
            for s in sorted(sinistros, key=lambda s: s.data_ocorrencia, reverse=True)
        ],
        "oportunidades": [
            {"id": o.id, "titulo": o.titulo, "ramo": o.ramo, "fase": o.fase, "valor_estimado": o.valor_estimado}
            for o in c.oportunidades
        ],
        "actividades": [
            {"id": a.id, "tipo": a.tipo, "assunto": a.assunto, "data": a.data.isoformat(), "concluida": a.concluida}
            for a in sorted(c.actividades, key=lambda a: a.data, reverse=True)[:20]
        ],
    }


def registar_actividade(db: Session, cliente_id: int, tipo: str, assunto: str, descricao: str | None = None) -> dict:
    if db.get(Cliente, cliente_id) is None:
        raise ValueError(f"cliente {cliente_id} não existe")
    if tipo not in ("chamada", "email", "reuniao", "nota", "tarefa"):
        raise ValueError(f"tipo de actividade inválido: {tipo}")
    act = Actividade(cliente_id=cliente_id, tipo=tipo, assunto=assunto, descricao=descricao, data=date.today())
    db.add(act)
    db.commit()
    return {"id": act.id, "cliente_id": cliente_id, "tipo": tipo, "assunto": assunto}


def painel(db: Session) -> dict:
    activas = select(Apolice).where(Apolice.estado == "activa").subquery()
    n_activas, premio = db.execute(
        select(func.count(), func.coalesce(func.sum(activas.c.premio_anual), 0)).select_from(activas)
    ).one()
    ren = renovacoes(db, 90)
    abertos = sinistros_abertos(db)
    pipe = pipeline(db)
    por_ramo = db.execute(
        select(Apolice.ramo, func.count(), func.sum(Apolice.premio_anual))
        .where(Apolice.estado == "activa")
        .group_by(Apolice.ramo)
        .order_by(func.sum(Apolice.premio_anual).desc())
    ).all()
    return {
        "clientes": db.scalar(select(func.count()).select_from(Cliente)),
        "apolices_activas": n_activas,
        "premio_anual_activo": float(premio),
        "renovacoes_30": sum(1 for r in ren if r["dias_restantes"] <= 30),
        "renovacoes_60": sum(1 for r in ren if r["dias_restantes"] <= 60),
        "renovacoes_90": len(ren),
        "sinistros_abertos": len(abertos),
        "valor_sinistros_abertos": sum(s["valor_reclamado"] for s in abertos),
        "pipeline_aberto": sum(p["valor"] for p in pipe if p["fase"] in FASES_ABERTAS),
        "pipeline": pipe,
        "por_ramo": [{"ramo": r, "apolices": n, "premio": float(p)} for r, n, p in por_ramo],
        "proximas_renovacoes": ren[:10],
    }
