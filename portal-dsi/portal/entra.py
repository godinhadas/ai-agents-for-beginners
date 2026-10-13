"""Início de sessão com conta Microsoft (Entra ID), fluxo OpenID Connect com código de autorização.

Activa-se com PORTAL_AUTH_MODE=entra. A aplicação é registada como single tenant, por isso só
contas do tenant da MHAIS conseguem entrar. Redirect URI a registar: {PORTAL_URL_BASE}/auth/callback
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Utilizador

log = logging.getLogger("portal.entra")
router = APIRouter(tags=["auth"])


def _app():
    import msal

    return msal.ConfidentialClientApplication(
        os.environ["ENTRA_CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{os.environ['ENTRA_TENANT_ID']}",
        client_credential=os.environ["ENTRA_CLIENT_SECRET"],
    )


def _redirect_uri() -> str:
    return os.getenv("PORTAL_URL_BASE", "http://localhost:8010").rstrip("/") + "/auth/callback"


def admins() -> set[str]:
    return {e.strip().lower() for e in os.getenv("PORTAL_ADMINS", "").split(",") if e.strip()}


def utilizador_de_claims(db: Session, claims: dict) -> Utilizador:
    """Associa a conta Microsoft a um utilizador do portal (cria-o se não existir)."""
    if claims.get("tid") != os.getenv("ENTRA_TENANT_ID"):
        raise PermissionError("Conta de outra organização.")
    oid = claims.get("oid")
    email = (claims.get("email") or claims.get("preferred_username") or "").strip().lower()
    if not oid or not email:
        raise PermissionError("A conta Microsoft não devolveu identificador ou email.")
    u = db.scalar(select(Utilizador).where(Utilizador.entra_oid == oid)) or \
        db.scalar(select(Utilizador).where(func.lower(Utilizador.email) == email))
    if u is None:
        if os.getenv("PORTAL_AUTO_CRIAR", "1") != "1":
            raise PermissionError("Utilizador ainda não registado no portal. Contacte a DSI.")
        u = Utilizador(nome=claims.get("name") or email, email=email, perfil="colaborador", activo=True)
        db.add(u)
    elif not u.activo:
        raise PermissionError("Utilizador desactivado no portal. Contacte a DSI.")
    u.entra_oid = oid
    if email in admins():
        u.perfil = "admin"
    db.commit()
    return u


@router.get("/auth/login", include_in_schema=False)
def login(request: Request):
    if os.getenv("PORTAL_AUTH_MODE") != "entra":
        raise HTTPException(404)
    fluxo = _app().initiate_auth_code_flow(scopes=["User.Read"], redirect_uri=_redirect_uri())
    request.session["fluxo"] = fluxo
    return RedirectResponse(fluxo["auth_uri"])


@router.get("/auth/callback", include_in_schema=False)
def callback(request: Request, db: Session = Depends(get_db)):
    if os.getenv("PORTAL_AUTH_MODE") != "entra":
        raise HTTPException(404)
    fluxo = request.session.pop("fluxo", None)
    if not fluxo:
        return RedirectResponse("/")
    try:
        r = _app().acquire_token_by_auth_code_flow(fluxo, dict(request.query_params))
    except ValueError:  # state inválido (CSRF) ou fluxo expirado
        return RedirectResponse("/")
    if "id_token_claims" not in r:
        log.warning("Login Entra falhou: %s", r.get("error_description") or r.get("error"))
        raise HTTPException(401, "Não foi possível validar a conta Microsoft.")
    try:
        u = utilizador_de_claims(db, r["id_token_claims"])
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    request.session.clear()
    request.session["uid"] = u.id
    return RedirectResponse("/#inicio")
