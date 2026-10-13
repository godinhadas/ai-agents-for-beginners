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
ESTADOS = {"em_aprovacao": "Em aprovação", "novo": "Novo", "em_curso": "Em curso",
           "aguarda_colaborador": "A aguardar colaborador", "resolvido": "Resolvido", "fechado": "Fechado",
           "recusado": "Recusado", "cancelado": "Cancelado"}

# accao -> (quem recebe, frase do assunto)
REGRAS = {
    "criado": (("criado_por", "beneficiario"), "Pedido registado"),
    "aguarda_aprovacao": ((), "Aprovação necessária"),  # vai para os administradores DSI
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
    """Email simples em HTML, com a identidade da empresa e compatível com o Outlook (tabelas e estilos inline)."""
    e = html.escape
    empresa = os.getenv("PORTAL_EMPRESA", "MHAIS")
    portal = os.getenv("PORTAL_NOME", "Gestor de Pedidos DSI")
    direccao = os.getenv("PORTAL_DIRECCAO", "Direcção de Sistemas de Informação")
    cor = os.getenv("PORTAL_COR_EMAIL", "#7a3ec8")
    escura = os.getenv("PORTAL_COR_EMAIL_ESCURA", "#2b0e43")
    detalhe_html = f"<p style='white-space:pre-wrap;margin:16px 0'>{e(detalhe)}</p>" if detalhe else ""
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-family:Segoe UI,Arial,sans-serif;color:#1d2533">
<tr><td style="background:{e(escura)};color:#ffffff;padding:16px 20px;font-size:16px;font-weight:bold;border-bottom:4px solid {e(cor)}">{e(empresa)} · {e(portal)}</td></tr>
<tr><td style="padding:20px;font-size:14px;line-height:1.5">
<p style="margin:0 0 12px;font-size:16px"><strong>{e(frase)}</strong></p>
<p style="margin:0">{e(p.numero)} · {e(p.titulo)}<br>Para: {e(p.beneficiario.nome)}<br>Estado: {e(ESTADOS.get(p.estado, p.estado))}</p>
{detalhe_html}
<p style="margin:20px 0"><a href="{e(_link(p))}" style="background:{e(cor)};color:#ffffff;padding:10px 16px;text-decoration:none;border-radius:4px">Abrir o pedido</a></p>
<p style="color:#667085;font-size:12px;margin:0">Pode responder a este email para acrescentar um comentário ao pedido. Mantenha o número entre parênteses rectos no assunto.</p>
</td></tr>
<tr><td style="padding:12px 20px;border-top:1px solid #e3e7ee;color:#667085;font-size:12px">{e(empresa)} · {e(direccao)}</td></tr>
</table>"""


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
    if accao == "aguarda_aprovacao":
        admins = db.scalars(select(Utilizador).where(Utilizador.perfil == "admin", Utilizador.activo)).all()
        _enfileirar(db, p, list(admins), frase, p.descricao, autor)
        return
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
