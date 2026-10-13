"""Notificações por email.

As mensagens são gravadas na tabela notificacoes (caixa de saída) na mesma transacção
do pedido e enviadas em segundo plano pela caixa do Helpdesk via Microsoft Graph.
Sem Graph configurado ficam como "simulada", visíveis em Administração.
"""

import html
import logging
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Notificacao, Pedido, Utilizador, agora

log = logging.getLogger("portal.email")
MAX_TENTATIVAS = 5

# accao -> (quem recebe, frase do assunto)
REGRAS = {
    "criado": (("criado_por", "beneficiario"), "Pedido registado"),
    "aguarda_aprovacao": (("aprovador",), "Aprovação necessária"),
    "aprovado": (("criado_por", "beneficiario"), "Pedido aprovado"),
    "recusado": (("criado_por", "beneficiario"), "Pedido recusado"),
    "atribuido": (("tecnico",), "Pedido atribuído a si"),
    "aguarda_colaborador": (("criado_por", "beneficiario"), "Precisamos de mais informação"),
    "resolvido": (("criado_por", "beneficiario"), "Pedido resolvido"),
    "reaberto": (("tecnico",), "Pedido reaberto"),
    "equipamento_entregue": (("beneficiario",), "Equipamento entregue"),
    "licenca_atribuida": (("beneficiario",), "Licença atribuída"),
    "cancelado": (("tecnico",), "Pedido cancelado"),
}


def caixa_helpdesk() -> str | None:
    return os.getenv("PORTAL_CAIXA_HELPDESK")


def _link(p: Pedido) -> str:
    base = os.getenv("PORTAL_URL_BASE", "http://127.0.0.1:8010").rstrip("/")
    return f"{base}/#pedido/{p.id}"


def assunto(p: Pedido, frase: str) -> str:
    # O número entre parênteses rectos permite associar as respostas por email ao pedido.
    return f"[{p.numero}] {frase}: {p.titulo}"[:250]


def _corpo(p: Pedido, frase: str, detalhe: str | None) -> str:
    e = html.escape
    linhas = [
        f"<p><strong>{e(frase)}</strong></p>",
        f"<p>{e(p.numero)} · {e(p.titulo)}<br>Para: {e(p.beneficiario.nome)}<br>Estado: {e(p.estado)}</p>",
    ]
    if detalhe:
        linhas.append(f"<p style='white-space:pre-wrap'>{e(detalhe)}</p>")
    linhas.append(f"<p><a href='{e(_link(p))}'>Abrir o pedido no Portal DSI</a></p>")
    linhas.append("<p style='color:#667085;font-size:12px'>Pode responder a este email para acrescentar um comentário "
                  "ao pedido. Mantenha o número entre parênteses rectos no assunto.</p>")
    return "\n".join(linhas)


def _enfileirar(db: Session, p: Pedido, destinatarios: list[Utilizador], frase: str, detalhe: str | None,
                autor: Utilizador | None) -> None:
    vistos: set[str] = set()
    for u in destinatarios:
        if u is None or not u.activo or (autor and u.id == autor.id):
            continue
        email = u.email.lower()
        if email in vistos or email == (caixa_helpdesk() or "").lower():
            continue
        vistos.add(email)
        db.add(Notificacao(pedido_id=p.id, para=u.email, assunto=assunto(p, frase), corpo=_corpo(p, frase, detalhe)))


def evento(db: Session, p: Pedido, autor: Utilizador | None, accao: str, detalhe: str | None) -> None:
    if accao not in REGRAS:
        return
    papeis, frase = REGRAS[accao]
    # Pelos ids (e não pelas relações), porque a relação pode ainda não reflectir um id acabado de mudar.
    _enfileirar(db, p, [db.get(Utilizador, i) for papel in papeis if (i := getattr(p, f"{papel}_id"))],
                frase, detalhe, autor)


def comentario(db: Session, p: Pedido, autor: Utilizador, texto: str, autor_e_staff: bool) -> None:
    if autor_e_staff:
        _enfileirar(db, p, [db.get(Utilizador, p.criado_por_id), db.get(Utilizador, p.beneficiario_id)],
                    "Nova resposta da DSI", texto, autor)
    elif p.tecnico_id:
        _enfileirar(db, p, [db.get(Utilizador, p.tecnico_id)], f"Comentário de {autor.nome}", texto, autor)


def novo_para_helpdesk(db: Session, p: Pedido) -> None:
    """Aviso à equipa quando um pedido fica disponível para tratamento."""
    if os.getenv("PORTAL_NOTIFICAR_HELPDESK", "1") != "1" or p.tecnico_id:
        return
    equipa = db.scalars(select(Utilizador).where(Utilizador.perfil == "helpdesk", Utilizador.activo)).all()
    _enfileirar(db, p, list(equipa), "Novo pedido para tratar", p.descricao, p.criado_por)


def enviar_pendentes(db: Session, graph, limite: int = 50) -> dict:
    pendentes = db.scalars(select(Notificacao).where(Notificacao.estado.in_(("pendente", "erro")),
                                                     Notificacao.tentativas < MAX_TENTATIVAS)
                           .order_by(Notificacao.id).limit(limite)).all()
    caixa = caixa_helpdesk()
    resumo = {"enviadas": 0, "simuladas": 0, "erros": 0}
    for n in pendentes:
        if graph is None or not caixa:
            n.estado, n.enviado_em = "simulada", agora()
            resumo["simuladas"] += 1
            continue
        n.tentativas += 1
        try:
            graph.post(f"/users/{caixa}/sendMail", {
                "message": {
                    "subject": n.assunto,
                    "body": {"contentType": "HTML", "content": n.corpo},
                    "toRecipients": [{"emailAddress": {"address": n.para}}],
                },
                "saveToSentItems": True,
            })
            n.estado, n.enviado_em, n.erro = "enviada", agora(), None
            resumo["enviadas"] += 1
        except Exception as exc:  # rede, permissões, caixa inexistente
            n.estado, n.erro = "erro", str(exc)[:1000]
            resumo["erros"] += 1
            log.warning("Falha a enviar notificação %s para %s: %s", n.id, n.para, exc)
    db.commit()
    return resumo
