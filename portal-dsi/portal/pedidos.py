"""Circuito do pedido: criação, aprovação, tratamento, entrega e fecho.

Toda a regra de negócio e de permissões dos pedidos vive aqui; a API só traduz
PermissionError em 403 e ValueError em 409/422.
"""

import os
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

import json

from . import automacoes, formularios, notificacoes, sla
from .models import (AtribuicaoLicenca, Comentario, Equipamento, Evento, ItemCatalogo, Licenca, Pedido,
                     Utilizador, agora)

ABERTOS = ("em_aprovacao", "novo", "em_curso", "aguarda_colaborador")


def inventario_activo() -> bool:
    """Módulo de equipamentos e licenças (desligado por omissão nesta fase)."""
    return os.getenv("PORTAL_INVENTARIO", "0") == "1"
DIAS_FECHO_AUTOMATICO = 5


def staff(u: Utilizador) -> bool:
    return u.perfil in ("helpdesk", "admin")


def pode_ver(u: Utilizador, p: Pedido) -> bool:
    return staff(u) or u.id in (p.criado_por_id, p.beneficiario_id)


def _evento(db: Session, p: Pedido, u: Utilizador | None, accao: str, detalhe: str | None = None) -> None:
    db.add(Evento(pedido=p, autor_id=u.id if u else None, accao=accao, detalhe=detalhe, criado_em=agora()))
    p.actualizado_em = agora()
    notificacoes.evento(db, p, u, accao, detalhe)


def _iniciar_sla(p: Pedido, inicio: datetime) -> None:
    p.sla_inicio = inicio
    p.prazo_resposta, p.prazo_resolucao = sla.prazos(p.prioridade, inicio)


def criar(db: Session, u: Utilizador, *, titulo: str | None = None, descricao: str = "",
          beneficiario_id: int | None = None, item_id: int | None = None, tipo: str | None = None,
          prioridade: str | None = None, origem: str = "portal", dados: dict | None = None) -> Pedido:
    beneficiario = db.get(Utilizador, beneficiario_id or u.id)
    if beneficiario is None or not beneficiario.activo:
        raise ValueError("Beneficiário inexistente ou inactivo.")
    item = None
    if item_id is not None:
        item = db.get(ItemCatalogo, item_id)
        if item is None or not item.activo:
            raise ValueError("Item do catálogo inexistente ou inactivo.")
    tipo = item.tipo if item else tipo
    if tipo is None:
        raise ValueError("Indica o item do catálogo ou o tipo de pedido.")
    respostas = formularios.validar(item.campos if item else None, dados)
    descricao = (descricao or "").strip()
    if not respostas and len(descricao) < 3:
        raise ValueError("Descreve o pedido.")
    titulo = (titulo or "").strip()
    if len(titulo) < 3:
        base = item.nome if item else "Pedido"
        titulo = f"{base}: {formularios.resumo(respostas)}" if respostas else base
    titulo = titulo[:200]
    prioridade = prioridade or (item.prioridade_padrao if item else "media")
    if prioridade == "critica" and not staff(u):
        prioridade = "alta"  # só a DSI classifica como crítico, para evitar abusos

    momento = agora()
    p = Pedido(titulo=titulo, descricao=descricao, tipo=tipo, item=item, prioridade=prioridade, estado="novo",
               origem=origem, dados=json.dumps(respostas, ensure_ascii=False) if respostas else None, criado_por_id=u.id, beneficiario=beneficiario, criado_em=momento, actualizado_em=momento)
    _iniciar_sla(p, momento)
    db.add(p)
    db.flush()
    detalhe = None if beneficiario.id == u.id else f"Em nome de {beneficiario.nome}"
    _evento(db, p, u, "criado", detalhe)

    # Equipamento, licenças e acessos são aprovados pela DSI (perfil administrador).
    if item and item.requer_aprovacao:
        if u.perfil == "admin":
            p.estado = "novo"
            p.aprovador_id = u.id
            _evento(db, p, u, "aprovado", "Aprovado automaticamente: pedido registado pela DSI")
        else:
            p.estado = "em_aprovacao"
            _evento(db, p, None, "aguarda_aprovacao")
    else:
        p.estado = "novo"
    if p.estado == "novo" and automacoes.imediata(p):
        _automatizar(db, p, u)
    if p.estado == "novo":
        notificacoes.novo_para_helpdesk(db, p)
    db.commit()
    return p


def _automatizar(db: Session, p: Pedido, u: Utilizador) -> bool:
    ok, msg = automacoes.executar(p)
    _evento(db, p, u if staff(u) else None, "automacao", ("Concluída: " if ok else "Falhou: ") + msg)
    if ok:
        p.estado = "resolvido"
        p.resolvido_em = agora()
        p.primeira_resposta_em = p.primeira_resposta_em or p.resolvido_em
        if staff(u):
            p.tecnico_id = p.tecnico_id or u.id
        _evento(db, p, u if staff(u) else None, "resolvido", f"Resolvido automaticamente. {msg}")
    return ok


def accoes(u: Utilizador, p: Pedido) -> list[str]:
    """Acções que o utilizador pode executar neste momento (a interface mostra só estas)."""
    a: list[str] = []
    envolvido = u.id in (p.criado_por_id, p.beneficiario_id)
    if p.estado == "em_aprovacao" and u.perfil == "admin":
        a += ["aprovar", "recusar"]
    if staff(u) and p.estado in ("novo", "em_curso", "aguarda_colaborador"):
        a += ["atribuir", "prioridade"]
        if p.tecnico_id != u.id:
            a.append("assumir")
        if p.estado != "aguarda_colaborador":
            a.append("aguardar")
        a.append("resolver")
        if automacoes.aplicavel(p):
            a.insert(0, "automatizar")
        if inventario_activo():
            a += ["entregar_equipamento", "atribuir_licenca"]
    if p.estado == "resolvido" and (envolvido or staff(u)):
        a += ["reabrir", "fechar"]
    if p.estado in ("em_aprovacao", "novo") and (envolvido or staff(u)):
        a.append("cancelar")
    return a


def executar(db: Session, u: Utilizador, p: Pedido, accao: str, dados: dict) -> Pedido:
    if accao not in accoes(u, p):
        raise PermissionError(f"Acção '{accao}' não permitida neste pedido.")
    momento = agora()
    motivo = (dados.get("motivo") or "").strip() or None

    if accao == "aprovar":
        p.estado = "novo"
        p.aprovador_id = u.id
        _iniciar_sla(p, momento)  # o SLA conta a partir da aprovação
        _evento(db, p, u, "aprovado", motivo)
        notificacoes.novo_para_helpdesk(db, p)
    elif accao == "recusar":
        if not motivo:
            raise ValueError("Indica o motivo da recusa.")
        p.estado = "recusado"
        p.aprovador_id = u.id
        p.fechado_em = momento
        _evento(db, p, u, "recusado", motivo)
    elif accao in ("atribuir", "assumir"):
        tecnico = u if accao == "assumir" else db.get(Utilizador, dados.get("tecnico_id") or 0)
        if tecnico is None or not staff(tecnico):
            raise ValueError("O técnico tem de ser do Helpdesk ou da DSI.")
        p.tecnico_id = tecnico.id
        if p.estado == "novo":
            p.estado = "em_curso"
        p.primeira_resposta_em = p.primeira_resposta_em or momento
        _evento(db, p, u, "atribuido", f"Técnico: {tecnico.nome}")
    elif accao == "prioridade":
        nova = dados.get("prioridade")
        if nova not in sla.SLA:
            raise ValueError("Prioridade inválida.")
        antiga, p.prioridade = p.prioridade, nova
        _iniciar_sla(p, p.sla_inicio)
        _evento(db, p, u, "prioridade", f"{antiga} → {nova}")
    elif accao == "aguardar":
        p.estado = "aguarda_colaborador"
        p.primeira_resposta_em = p.primeira_resposta_em or momento
        _evento(db, p, u, "aguarda_colaborador", motivo)
    elif accao == "resolver":
        if not motivo:
            raise ValueError("Descreve a solução aplicada.")
        p.estado = "resolvido"
        p.resolvido_em = momento
        p.tecnico_id = p.tecnico_id or u.id
        p.primeira_resposta_em = p.primeira_resposta_em or momento
        _evento(db, p, u, "resolvido", motivo)
    elif accao == "reabrir":
        if not motivo:
            raise ValueError("Indica porque reabres o pedido.")
        p.estado = "em_curso"
        p.resolvido_em = None
        _evento(db, p, u, "reaberto", motivo)
    elif accao == "fechar":
        p.estado = "fechado"
        p.fechado_em = momento
        _evento(db, p, u, "fechado", motivo)
    elif accao == "automatizar":
        if not _automatizar(db, p, u):
            p.primeira_resposta_em = p.primeira_resposta_em or momento
    elif accao == "cancelar":
        p.estado = "cancelado"
        p.fechado_em = momento
        _evento(db, p, u, "cancelado", motivo)
    elif accao == "entregar_equipamento":
        eq = db.get(Equipamento, dados.get("equipamento_id") or 0)
        if eq is None or eq.estado != "stock":
            raise ValueError("Equipamento inexistente ou fora de stock.")
        eq.estado, eq.utilizador_id = "atribuido", p.beneficiario_id
        _evento(db, p, u, "equipamento_entregue", f"{eq.etiqueta} ({eq.tipo} {eq.marca or ''} {eq.modelo or ''})".strip())
    elif accao == "atribuir_licenca":
        lic = db.get(Licenca, dados.get("licenca_id") or 0)
        if lic is None:
            raise ValueError("Licença inexistente.")
        if any(a.utilizador_id == p.beneficiario_id for a in lic.atribuicoes):
            raise ValueError("O beneficiário já tem esta licença.")
        if len(lic.atribuicoes) >= lic.quantidade:
            raise ValueError(f"Sem licenças livres de {lic.produto}.")
        lic.atribuicoes.append(AtribuicaoLicenca(utilizador_id=p.beneficiario_id))
        _evento(db, p, u, "licenca_atribuida", lic.produto)
    db.commit()
    return p


def comentar(db: Session, u: Utilizador, p: Pedido, texto: str, interno: bool = False) -> Comentario:
    if interno and not staff(u):
        raise PermissionError("Só a DSI pode criar notas internas.")
    if p.estado in ("fechado", "recusado", "cancelado"):
        raise ValueError("Pedido encerrado: não aceita comentários.")
    c = Comentario(pedido=p, autor_id=u.id, texto=texto, interno=interno, criado_em=agora())
    db.add(c)
    if staff(u) and not interno:
        p.primeira_resposta_em = p.primeira_resposta_em or c.criado_em
    if not interno:
        notificacoes.comentario(db, p, u, texto, staff(u))
    if p.estado == "aguarda_colaborador" and u.id in (p.criado_por_id, p.beneficiario_id):
        p.estado = "em_curso"
        _evento(db, p, u, "resposta_colaborador")
    p.actualizado_em = agora()
    db.commit()
    return c


def fechar_automaticamente(db: Session) -> int:
    limite = agora() - timedelta(days=DIAS_FECHO_AUTOMATICO)
    pendentes = db.scalars(select(Pedido).where(Pedido.estado == "resolvido", Pedido.resolvido_em < limite)).all()
    for p in pendentes:
        p.estado = "fechado"
        p.fechado_em = agora()
        _evento(db, p, None, "fechado", f"Fecho automático após {DIAS_FECHO_AUTOMATICO} dias resolvido")
    if pendentes:
        db.commit()
    return len(pendentes)
