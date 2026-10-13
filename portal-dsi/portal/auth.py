"""Autenticação e perfis.

PORTAL_AUTH_MODE=dev (por omissão): escolhe-se o utilizador numa lista, sem
palavra-passe. Serve só para desenvolvimento e demonstração, nunca em rede.
O início de sessão com contas Microsoft (Entra ID) entra na etapa 1b.
"""

import os

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import Utilizador


def modo() -> str:
    return os.getenv("PORTAL_AUTH_MODE", "dev")


def utilizador_actual(request: Request, db: Session = Depends(get_db)) -> Utilizador:
    uid = request.session.get("uid")
    u = db.get(Utilizador, uid) if uid else None
    if u is None or not u.activo:
        request.session.clear()
        raise HTTPException(401, "Sessão inválida ou expirada. Inicia sessão.")
    return u


def exigir(*perfis: str):
    def _dep(u: Utilizador = Depends(utilizador_actual)) -> Utilizador:
        if u.perfil not in perfis:
            raise HTTPException(403, "Sem permissão para esta operação.")
        return u

    return _dep


STAFF = ("helpdesk", "admin")
