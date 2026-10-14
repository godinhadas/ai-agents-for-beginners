"""Novidades no portal: mensagens e mudanças que o utilizador ainda não viu.

Cada pessoa vê só o que lhe diz respeito:
- requerente (quem pediu ou o beneficiário): mensagens da DSI e mudanças do pedido
  (aprovado, assumido, pedido de informação, resolvido, ...);
- técnico atribuído: mensagens do colaborador, reaberturas, confirmações e cancelamentos;
- Helpdesk e DSI: pedidos novos ainda sem técnico e mensagens nesses pedidos;
- administradores DSI: pedidos à espera de aprovação.
Uma novidade deixa de o ser quando a pessoa abre o pedido (tabela leituras, pela última
mensagem e último evento vistos, para não depender de segundos iguais).
"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Comentario, Evento, Leitura, Pedido, Utilizador, agora

JANELA_DIAS = 30
MAXIMO = 30

EVENTOS_REQUERENTE = {
    "aprovado": "Pedido aprovado", "recusado": "Pedido recusado", "atribuido": "Pedido assumido por um técnico",
    "aguarda_colaborador": "A DSI precisa de mais informação", "resolvido": "Pedido resolvido: confirma se ficou resolvido",
    "fechado": "Pedido fechado", "equipamento_entregue": "Equipamento entregue", "licenca_atribuida": "Licença atribuída",
    "automacao": "Resolvido automaticamente",
}
EVENTOS_TECNICO = {
    "atribuido": "Pedido atribuído a ti", "reaberto": "Pedido reaberto pelo colaborador",
    "fechado": "Resolução confirmada", "cancelado": "Pedido cancelado",
}


def _staff(u: Utilizador) -> bool:
    return u.perfil in ("helpdesk", "admin")


def _papeis(u: Utilizador, p: Pedido) -> set[str]:
    r = set()
    if u.id in (p.criado_por_id, p.beneficiario_id):
        r.add("requerente")
    if p.tecnico_id == u.id:
        r.add("tecnico")
    if _staff(u) and p.tecnico_id is None and p.estado in ("novo", "em_curso", "aguarda_colaborador"):
        r.add("equipa")
    if u.perfil == "admin" and p.estado == "em_aprovacao":
        r.add("aprovador")
    return r


def _frase_evento(e: Evento, papeis: set[str]) -> str | None:
    if "requerente" in papeis and e.accao in EVENTOS_REQUERENTE:
        return EVENTOS_REQUERENTE[e.accao]
    if "tecnico" in papeis and e.accao in EVENTOS_TECNICO:
        return EVENTOS_TECNICO[e.accao]
    if "equipa" in papeis and e.accao in ("criado", "aprovado", "reaberto"):
        return "Novo pedido para tratar" if e.accao != "reaberto" else "Pedido reaberto"
    if "aprovador" in papeis and e.accao == "aguarda_aprovacao":
        return "Pedido à espera da tua aprovação"
    return None


def listar(db: Session, u: Utilizador) -> list[dict]:
    """Novidades por ler, mais recentes primeiro."""
    desde = agora() - timedelta(days=JANELA_DIAS)
    vistos = {l.pedido_id: l for l in db.scalars(select(Leitura).where(Leitura.utilizador_id == u.id))}
    cache: dict[int, set[str]] = {}

    def papeis(p: Pedido) -> set[str]:
        if p.id not in cache:
            cache[p.id] = _papeis(u, p)
        return cache[p.id]

    def nova_msg(c: Comentario) -> bool:
        l = vistos.get(c.pedido_id)
        return l is None or c.id > l.comentario_id

    def novo_evento(e: Evento) -> bool:
        l = vistos.get(e.pedido_id)
        return l is None or e.id > l.evento_id

    itens: list[dict] = []
    for c in db.scalars(select(Comentario).where(Comentario.criado_em >= desde, Comentario.autor_id != u.id)):
        p = c.pedido
        if c.interno and not _staff(u):
            continue
        if not papeis(p) - {"aprovador"} or not nova_msg(c):
            continue
        itens.append({"pedido_id": p.id, "numero": p.numero, "titulo": p.titulo, "tipo": "mensagem",
                      "texto": c.texto[:160], "autor": c.autor.nome, "criado_em": c.criado_em})
    for e in db.scalars(select(Evento).where(Evento.criado_em >= desde)):
        if e.autor_id == u.id:
            continue
        p = e.pedido
        frase = _frase_evento(e, papeis(p))
        if frase is None or not novo_evento(e):
            continue
        itens.append({"pedido_id": p.id, "numero": p.numero, "titulo": p.titulo, "tipo": "estado",
                      "texto": frase + (f": {e.detalhe[:120]}" if e.detalhe and e.accao != "atribuido" else ""),
                      "autor": e.autor.nome if e.autor else "Sistema", "criado_em": e.criado_em})
    itens.sort(key=lambda i: i["criado_em"], reverse=True)
    return itens


def resumo(db: Session, u: Utilizador) -> dict:
    itens = listar(db, u)
    return {"total": len(itens), "pedidos": sorted({i["pedido_id"] for i in itens}), "itens": itens[:MAXIMO]}


def pedidos_com_novidades(db: Session, u: Utilizador) -> set[int]:
    return {i["pedido_id"] for i in listar(db, u)}


def _ultimos(db: Session, pedido_id: int) -> tuple[int, int]:
    return (db.scalar(select(func.max(Comentario.id)).where(Comentario.pedido_id == pedido_id)) or 0,
            db.scalar(select(func.max(Evento.id)).where(Evento.pedido_id == pedido_id)) or 0)


def _registar(db: Session, u: Utilizador, pedido_id: int) -> Leitura | None:
    l = db.scalar(select(Leitura).where(Leitura.utilizador_id == u.id, Leitura.pedido_id == pedido_id))
    anterior = None if l is None else (l.comentario_id, l.evento_id)
    if l is None:
        l = Leitura(utilizador_id=u.id, pedido_id=pedido_id)
        db.add(l)
    l.visto_em = agora()
    l.comentario_id, l.evento_id = _ultimos(db, pedido_id)
    return anterior


def marcar_visto(db: Session, u: Utilizador, pedido_id: int) -> tuple[int, int] | None:
    """Regista a leitura; devolve (última mensagem, último evento) vistos antes desta (None se for a primeira)."""
    anterior = _registar(db, u, pedido_id)
    db.commit()
    return anterior


def marcar_tudo(db: Session, u: Utilizador) -> int:
    ids = pedidos_com_novidades(db, u)
    for pid in ids:
        _registar(db, u, pid)
    db.commit()
    return len(ids)
