"""Sincronização de colaboradores e departamentos a partir do Entra ID.

Regras:
- o Entra ID é a fonte de verdade para nome, email, departamento, chefia directa (informativa) e estado;
- o perfil (colaborador, helpdesk, admin) é gerido no portal e nunca é alterado pela sincronização;
- contas desactivadas no Entra ID ficam inactivas no portal (o histórico mantém-se);
- com PORTAL_SYNC_GRUPO definido, só entram os membros desse grupo.

Uso manual: python -m portal.sincronizar
"""

import logging
import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Departamento, Utilizador

log = logging.getLogger("portal.sync")
CAMPOS = "id,displayName,mail,userPrincipalName,department,accountEnabled,userType"


def _ler_utilizadores(graph) -> list[dict]:
    grupo = os.getenv("PORTAL_SYNC_GRUPO")
    if grupo:
        caminho = f"/groups/{grupo}/transitiveMembers/microsoft.graph.user"
    else:
        caminho = "/users"
    us = graph.get_todos(caminho, params={"$select": CAMPOS, "$top": "999"})
    # Só contas de pessoas da organização, com caixa de correio.
    return [u for u in us if u.get("userType", "Member") == "Member" and (u.get("mail") or "").strip()]


def sincronizar(db: Session, graph) -> dict:
    remotos = _ler_utilizadores(graph)
    resumo = {"lidos": len(remotos), "criados": 0, "actualizados": 0, "desactivados": 0}

    deps = {d.nome.lower(): d for d in db.scalars(select(Departamento))}

    def departamento(nome: str | None) -> int | None:
        if not nome or not nome.strip():
            return None
        chave = nome.strip().lower()
        if chave not in deps:
            deps[chave] = Departamento(nome=nome.strip())
            db.add(deps[chave])
            db.flush()
        return deps[chave].id

    por_oid: dict[str, Utilizador] = {}
    for r in remotos:
        email = r["mail"].strip().lower()
        u = db.scalar(select(Utilizador).where(Utilizador.entra_oid == r["id"])) or \
            db.scalar(select(Utilizador).where(func.lower(Utilizador.email) == email))
        activo = bool(r.get("accountEnabled", True))
        if u is None:
            if not activo:
                continue
            u = Utilizador(nome=r["displayName"], email=email, perfil="colaborador", activo=True)
            db.add(u)
            resumo["criados"] += 1
        else:
            if u.activo and not activo:
                resumo["desactivados"] += 1
            if (u.nome, u.email.lower(), u.activo) != (r["displayName"], email, activo):
                resumo["actualizados"] += 1
        u.entra_oid = r["id"]
        u.nome = r["displayName"]
        u.email = email
        u.activo = activo
        u.departamento_id = departamento(r.get("department")) or u.departamento_id
        por_oid[r["id"]] = u
    db.flush()

    # Chefia directa (só informativa): segundo passo, quando já existem todos os utilizadores.
    for oid, u in por_oid.items():
        chefe = graph.get_opcional(f"/users/{oid}/manager", params={"$select": "id"})
        chefe_local = por_oid.get(chefe["id"]) if chefe else None
        u.chefia_id = chefe_local.id if chefe_local else None
    db.commit()
    log.info("Sincronização Entra ID: %s", resumo)
    return resumo
