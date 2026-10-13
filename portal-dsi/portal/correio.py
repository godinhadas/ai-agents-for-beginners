"""Pedidos por email: lê a caixa do Helpdesk e cria pedidos ou comentários.

- Email de um colaborador conhecido, sem número no assunto: cria um pedido (origem "email").
- Assunto com [PED-000123] de alguém envolvido no pedido: acrescenta um comentário.
- Remetente desconhecido, respostas automáticas e emails da própria caixa: ignorados.
Cada email é registado em mensagens_recebidas e marcado como lido, para nunca ser tratado duas vezes.
"""

import logging
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import pedidos as wf
from .models import MensagemRecebida, Pedido, Utilizador
from .notificacoes import caixa_helpdesk

log = logging.getLogger("portal.correio")
NUMERO = re.compile(r"\[PED-(\d{6})\]")
ENCERRADOS = ("fechado", "recusado", "cancelado")


def _automatica(msg: dict) -> bool:
    for h in msg.get("internetMessageHeaders") or []:
        nome, valor = h.get("name", "").lower(), h.get("value", "").lower()
        if nome == "auto-submitted" and valor != "no":
            return True
        if nome in ("x-autoreply", "x-autorespond") or (nome == "precedence" and valor in ("bulk", "auto_reply", "junk")):
            return True
    return False


def _texto(msg: dict) -> str:
    corpo = (msg.get("uniqueBody") or msg.get("body") or {}).get("content") or ""
    return corpo.strip()[:5000] or "(email sem texto)"


def processar_mensagem(db: Session, msg: dict) -> str:
    chave = msg.get("internetMessageId") or msg["id"]
    if db.scalar(select(MensagemRecebida.id).where(MensagemRecebida.message_id == chave)):
        return "duplicado"
    remetente = ((msg.get("from") or {}).get("emailAddress") or {}).get("address", "").strip().lower()
    assunto = (msg.get("subject") or "").strip()
    registo = MensagemRecebida(message_id=chave, remetente=remetente, resultado="ignorado")

    u = db.scalar(select(Utilizador).where(func.lower(Utilizador.email) == remetente, Utilizador.activo))
    if remetente == (caixa_helpdesk() or "").lower() or _automatica(msg) or u is None:
        if u is None:
            log.info("Email ignorado (remetente desconhecido): %s", remetente)
        db.add(registo)
        db.commit()
        return "ignorado"

    if (m := NUMERO.search(assunto)) and (p := db.get(Pedido, int(m.group(1)))) \
            and wf.pode_ver(u, p) and p.estado not in ENCERRADOS:
        wf.comentar(db, u, p, _texto(msg))
        registo.pedido_id, registo.resultado = p.id, "comentario"
    else:
        titulo = NUMERO.sub("", assunto).strip() or "(sem assunto)"
        p = wf.criar(db, u, titulo=titulo[:200], descricao=_texto(msg), tipo="outro", origem="email")
        registo.pedido_id, registo.resultado = p.id, "criado"
    db.add(registo)
    db.commit()
    return registo.resultado


def processar_caixa(db: Session, graph, limite: int = 25) -> dict:
    caixa = caixa_helpdesk()
    if not caixa:
        return {"erro": "PORTAL_CAIXA_HELPDESK não definido"}
    msgs = graph.get(
        f"/users/{caixa}/mailFolders/inbox/messages",
        params={"$filter": "isRead eq false", "$top": str(limite),
                "$select": "id,internetMessageId,subject,from,uniqueBody,body,receivedDateTime,internetMessageHeaders"},
        headers={"Prefer": 'outlook.body-content-type="text"'},
    ).get("value", [])
    resumo: dict[str, int] = {}
    for msg in sorted(msgs, key=lambda m: m.get("receivedDateTime", "")):
        try:
            r = processar_mensagem(db, msg)
        except Exception:
            db.rollback()
            log.exception("Falha a processar email %s", msg.get("id"))
            continue  # fica por ler e volta a ser tentado no ciclo seguinte
        graph.patch(f"/users/{caixa}/messages/{msg['id']}", {"isRead": True})
        resumo[r] = resumo.get(r, 0) + 1
    return resumo
