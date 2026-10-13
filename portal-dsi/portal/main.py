"""API e interface web do Portal DSI."""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import auth, db as dbmod, pedidos as wf, schemas as s, seed, sla
from .auth import STAFF, exigir, utilizador_actual
from .db import get_db
from .models import (AtribuicaoLicenca, Departamento, Equipamento, ItemCatalogo, Licenca, Pedido, Utilizador,
                     agora)

load_dotenv()
log = logging.getLogger("portal")
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    dbmod.init_db()
    if os.getenv("PORTAL_SEED", "1") == "1":
        with dbmod.SessionLocal() as db:
            seed.carregar(db)
    yield


app = FastAPI(title="Portal DSI MHAIS", version="0.1.0", lifespan=lifespan)

_segredo = os.getenv("PORTAL_SECRET_KEY")
if not _segredo:
    log.warning("PORTAL_SECRET_KEY não definido: sessões perdem-se ao reiniciar o servidor.")
    _segredo = secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=_segredo, session_cookie="portal_dsi", same_site="lax",
                   max_age=8 * 3600, https_only=os.getenv("PORTAL_HTTPS", "0") == "1")


# ---------- utilitários ----------

def _commit(db: Session, obj=None):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        msg = str(exc.orig).lower()
        if "unique" in msg:
            raise HTTPException(409, "Já existe um registo com esse identificador (email, etiqueta, nº de série ou nome).")
        raise HTTPException(409, "Operação recusada: o registo tem dependências ou referencia um registo inexistente.")
    if obj is not None:
        db.refresh(obj)


def _validar_refs(db: Session, model, dados: dict):
    for fk in model.__table__.foreign_keys:
        valor = dados.get(fk.parent.name)
        if valor is None:
            continue
        alvo = fk.column.table
        if db.execute(select(alvo.c.id).where(alvo.c.id == valor)).first() is None:
            raise HTTPException(422, f"{fk.parent.name}={valor} não existe.")


def _erro_regra(exc: Exception):
    if isinstance(exc, PermissionError):
        raise HTTPException(403, str(exc))
    raise HTTPException(409, str(exc))


def crud(nome: str, model, entrada, update, saida, *, leitura: tuple[str, ...], escrita: tuple[str, ...],
         pesquisa: tuple[str, ...], filtros: tuple[str, ...], ordem, apagar: bool = True,
         serializar=None) -> APIRouter:
    r = APIRouter(prefix=f"/api/{nome}", tags=[nome])
    ser = serializar or (lambda o: o)

    @r.get("", response_model=list[saida])
    def listar(request: Request, q: str | None = None, limit: int = Query(500, le=2000), offset: int = 0,
               db: Session = Depends(get_db), _=Depends(exigir(*leitura))):
        stmt = select(model)
        if q:
            stmt = stmt.where(or_(*(getattr(model, c).ilike(f"%{q}%") for c in pesquisa)))
        for f in filtros:
            if (v := request.query_params.get(f)) not in (None, ""):
                valor = {"true": True, "false": False}.get(v.lower(), v)
                stmt = stmt.where(getattr(model, f) == valor)
        return [ser(o) for o in db.scalars(stmt.order_by(ordem).limit(limit).offset(offset))]

    @r.post("", response_model=saida, status_code=201)
    def criar(dados: entrada, db: Session = Depends(get_db), _=Depends(exigir(*escrita))):  # type: ignore[valid-type]
        valores = dados.model_dump()
        _validar_refs(db, model, valores)
        obj = model(**valores)
        db.add(obj)
        _commit(db, obj)
        return ser(obj)

    @r.patch("/{item_id}", response_model=saida)
    def actualizar(item_id: int, dados: update, db: Session = Depends(get_db),  # type: ignore[valid-type]
                   _=Depends(exigir(*escrita))):
        if (obj := db.get(model, item_id)) is None:
            raise HTTPException(404, "Registo não encontrado.")
        alteracoes = dados.model_dump(exclude_unset=True)
        try:
            entrada.model_validate({**entrada.model_validate(obj).model_dump(), **alteracoes})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_url=False, include_context=False, include_input=False))
        _validar_refs(db, model, alteracoes)
        for k, v in alteracoes.items():
            setattr(obj, k, v)
        _commit(db, obj)
        return ser(obj)

    if apagar:
        @r.delete("/{item_id}", status_code=204)
        def remover(item_id: int, db: Session = Depends(get_db), _=Depends(exigir(*escrita))):
            if (obj := db.get(model, item_id)) is None:
                raise HTTPException(404, "Registo não encontrado.")
            db.delete(obj)
            _commit(db)
            return Response(status_code=204)

    return r


def _licenca_out(l: Licenca) -> dict:
    usadas = len(l.atribuicoes)
    return {**s.LicencaIn.model_validate(l).model_dump(), "id": l.id, "usadas": usadas,
            "livres": max(l.quantidade - usadas, 0)}


TODOS = ("colaborador", "chefia", "helpdesk", "admin")
for router in (
    crud("departamentos", Departamento, s.DepartamentoIn, s.DepartamentoUpdate, s.DepartamentoOut,
         leitura=TODOS, escrita=("admin",), pesquisa=("nome",), filtros=(), ordem=Departamento.nome),
    # Utilizadores não se apagam (desactivam-se) para manter o histórico dos pedidos.
    crud("utilizadores", Utilizador, s.UtilizadorIn, s.UtilizadorUpdate, s.UtilizadorOut,
         leitura=TODOS, escrita=("admin",), pesquisa=("nome", "email"),
         filtros=("departamento_id", "perfil", "chefia_id", "activo"), ordem=Utilizador.nome, apagar=False),
    crud("catalogo", ItemCatalogo, s.ItemCatalogoIn, s.ItemCatalogoUpdate, s.ItemCatalogoOut,
         leitura=TODOS, escrita=("admin",), pesquisa=("nome",), filtros=("tipo", "activo"),
         ordem=ItemCatalogo.nome, apagar=False),
    crud("equipamentos", Equipamento, s.EquipamentoIn, s.EquipamentoUpdate, s.EquipamentoOut,
         leitura=STAFF, escrita=STAFF, pesquisa=("etiqueta", "tipo", "marca", "modelo", "numero_serie"),
         filtros=("estado", "tipo", "utilizador_id"), ordem=Equipamento.etiqueta),
    crud("licencas", Licenca, s.LicencaIn, s.LicencaUpdate, s.LicencaOut,
         leitura=STAFF, escrita=("admin",), pesquisa=("produto", "fornecedor"), filtros=(),
         ordem=Licenca.produto, serializar=_licenca_out),
):
    app.include_router(router)


# ---------- sessão ----------

@app.get("/api/auth/modo", tags=["auth"])
def auth_modo():
    return {"modo": auth.modo()}


@app.get("/api/auth/utilizadores-demo", tags=["auth"])
def utilizadores_demo(db: Session = Depends(get_db)):
    if auth.modo() != "dev":
        raise HTTPException(404)
    us = db.scalars(select(Utilizador).where(Utilizador.activo).order_by(Utilizador.perfil, Utilizador.nome))
    return [{"id": u.id, "nome": u.nome, "perfil": u.perfil} for u in us]


@app.post("/api/auth/login", tags=["auth"])
def login(dados: s.LoginIn, request: Request, db: Session = Depends(get_db)):
    if auth.modo() != "dev":
        raise HTTPException(501, "Início de sessão com conta Microsoft ainda não configurado.")
    u = db.get(Utilizador, dados.utilizador_id)
    if u is None or not u.activo:
        raise HTTPException(401, "Utilizador inválido.")
    request.session["uid"] = u.id
    return {"id": u.id}


@app.post("/api/auth/logout", status_code=204, tags=["auth"])
def logout(request: Request):
    request.session.clear()
    return Response(status_code=204)


@app.get("/api/eu", tags=["auth"])
def eu(u: Utilizador = Depends(utilizador_actual)):
    return {"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil,
            "departamento": u.departamento.nome if u.departamento else None}


# ---------- pedidos ----------

def _resumo(p: Pedido, momento) -> dict:
    return {
        "id": p.id, "numero": p.numero, "titulo": p.titulo, "tipo": p.tipo, "item": p.item.nome if p.item else None,
        "prioridade": p.prioridade, "estado": p.estado, "beneficiario": p.beneficiario.nome,
        "criado_por": p.criado_por.nome, "tecnico": p.tecnico.nome if p.tecnico else None,
        "criado_em": p.criado_em, "actualizado_em": p.actualizado_em, "prazo_resolucao": p.prazo_resolucao,
        "sla": sla.estado_sla(p, momento),
    }


def _obter_pedido(db: Session, u: Utilizador, pedido_id: int) -> Pedido:
    p = db.get(Pedido, pedido_id)
    if p is None or not wf.pode_ver(u, p):
        raise HTTPException(404, "Pedido não encontrado.")
    return p


@app.get("/api/pedidos", response_model=list[s.PedidoResumo], tags=["pedidos"])
def listar_pedidos(vista: str | None = None, estado: str | None = None, q: str | None = None,
                   limit: int = Query(300, le=1000), db: Session = Depends(get_db),
                   u: Utilizador = Depends(utilizador_actual)):
    wf.fechar_automaticamente(db)
    vista = vista or ("todos" if wf.staff(u) else "meus")
    stmt = select(Pedido)
    if vista == "meus":
        stmt = stmt.where(or_(Pedido.criado_por_id == u.id, Pedido.beneficiario_id == u.id))
    elif vista == "aprovar":
        stmt = stmt.where(Pedido.estado == "em_aprovacao")
        if u.perfil != "admin":
            stmt = stmt.where(Pedido.aprovador_id == u.id)
    elif vista == "equipa":
        equipa = select(Utilizador.id).where(Utilizador.chefia_id == u.id)
        stmt = stmt.where(Pedido.beneficiario_id.in_(equipa))
    elif vista == "atribuidos" and wf.staff(u):
        stmt = stmt.where(Pedido.tecnico_id == u.id)
    elif vista == "todos" and wf.staff(u):
        pass
    else:
        raise HTTPException(400, "Vista inválida para o teu perfil.")
    if estado == "abertos":
        stmt = stmt.where(Pedido.estado.in_(wf.ABERTOS))
    elif estado:
        stmt = stmt.where(Pedido.estado == estado)
    if q:
        if q.upper().startswith("PED-") and q[4:].isdigit():
            stmt = stmt.where(Pedido.id == int(q[4:]))
        else:
            stmt = stmt.where(or_(Pedido.titulo.ilike(f"%{q}%"), Pedido.descricao.ilike(f"%{q}%")))
    momento = agora()
    return [_resumo(p, momento) for p in db.scalars(stmt.order_by(Pedido.id.desc()).limit(limit))]


@app.post("/api/pedidos", status_code=201, tags=["pedidos"])
def criar_pedido(dados: s.PedidoIn, db: Session = Depends(get_db), u: Utilizador = Depends(utilizador_actual)):
    try:
        p = wf.criar(db, u, **dados.model_dump())
    except (ValueError, PermissionError) as exc:
        _erro_regra(exc)
    return {"id": p.id, "numero": p.numero, "estado": p.estado}


@app.get("/api/pedidos/{pedido_id}", tags=["pedidos"])
def detalhe_pedido(pedido_id: int, db: Session = Depends(get_db), u: Utilizador = Depends(utilizador_actual)):
    p = _obter_pedido(db, u, pedido_id)
    ver_internos = wf.staff(u)
    return {
        **_resumo(p, agora()),
        "descricao": p.descricao,
        "beneficiario_id": p.beneficiario_id,
        "aprovador": p.aprovador.nome if p.aprovador else None,
        "prazo_resposta": p.prazo_resposta,
        "primeira_resposta_em": p.primeira_resposta_em,
        "resolvido_em": p.resolvido_em,
        "accoes": wf.accoes(u, p),
        "comentarios": [
            {"id": c.id, "autor": c.autor.nome, "texto": c.texto, "interno": c.interno, "criado_em": c.criado_em}
            for c in p.comentarios if ver_internos or not c.interno
        ],
        "eventos": [
            {"accao": e.accao, "detalhe": e.detalhe, "autor": e.autor.nome if e.autor else "Sistema",
             "criado_em": e.criado_em}
            for e in p.eventos
        ],
    }


@app.post("/api/pedidos/{pedido_id}/accoes/{accao}", tags=["pedidos"])
def accao_pedido(pedido_id: int, accao: str, dados: s.AccaoIn, db: Session = Depends(get_db),
                 u: Utilizador = Depends(utilizador_actual)):
    p = _obter_pedido(db, u, pedido_id)
    try:
        wf.executar(db, u, p, accao, dados.model_dump())
    except (ValueError, PermissionError) as exc:
        db.rollback()
        _erro_regra(exc)
    return {"id": p.id, "estado": p.estado}


@app.post("/api/pedidos/{pedido_id}/comentarios", status_code=201, tags=["pedidos"])
def comentar(pedido_id: int, dados: s.ComentarioIn, db: Session = Depends(get_db),
             u: Utilizador = Depends(utilizador_actual)):
    p = _obter_pedido(db, u, pedido_id)
    try:
        c = wf.comentar(db, u, p, dados.texto, dados.interno)
    except (ValueError, PermissionError) as exc:
        _erro_regra(exc)
    return {"id": c.id}


# ---------- licenças: atribuições ----------

@app.get("/api/licencas/{licenca_id}/atribuicoes", tags=["licencas"])
def atribuicoes(licenca_id: int, db: Session = Depends(get_db), _=Depends(exigir(*STAFF))):
    if (lic := db.get(Licenca, licenca_id)) is None:
        raise HTTPException(404, "Licença não encontrada.")
    return [{"utilizador_id": a.utilizador_id, "utilizador": a.utilizador.nome, "atribuida_em": a.atribuida_em}
            for a in sorted(lic.atribuicoes, key=lambda a: a.utilizador.nome)]


@app.delete("/api/licencas/{licenca_id}/atribuicoes/{utilizador_id}", status_code=204, tags=["licencas"])
def remover_atribuicao(licenca_id: int, utilizador_id: int, db: Session = Depends(get_db),
                       _=Depends(exigir(*STAFF))):
    a = db.scalar(select(AtribuicaoLicenca).where(AtribuicaoLicenca.licenca_id == licenca_id,
                                                  AtribuicaoLicenca.utilizador_id == utilizador_id))
    if a is None:
        raise HTTPException(404, "Atribuição não encontrada.")
    db.delete(a)
    _commit(db)
    return Response(status_code=204)


# ---------- painéis ----------

@app.get("/api/inicio", tags=["painel"])
def inicio(db: Session = Depends(get_db), u: Utilizador = Depends(utilizador_actual)):
    """Página inicial de qualquer colaborador."""
    momento = agora()
    meus = db.scalars(select(Pedido).where(or_(Pedido.criado_por_id == u.id, Pedido.beneficiario_id == u.id),
                                           Pedido.estado.in_(wf.ABERTOS + ("resolvido",)))
                      .order_by(Pedido.id.desc())).all()
    aprovar = select(Pedido).where(Pedido.estado == "em_aprovacao")
    if u.perfil != "admin":
        aprovar = aprovar.where(Pedido.aprovador_id == u.id)
    equipamentos = db.scalars(select(Equipamento).where(Equipamento.utilizador_id == u.id)).all()
    licencas = db.scalars(select(Licenca).join(AtribuicaoLicenca).where(AtribuicaoLicenca.utilizador_id == u.id)).all()
    return {
        "meus_pedidos": [_resumo(p, momento) for p in meus],
        "para_aprovar": [_resumo(p, momento) for p in db.scalars(aprovar.order_by(Pedido.id))],
        "equipamentos": [{"etiqueta": e.etiqueta, "tipo": e.tipo, "marca": e.marca, "modelo": e.modelo,
                          "numero_serie": e.numero_serie} for e in equipamentos],
        "licencas": [l.produto for l in licencas],
    }


@app.get("/api/painel", tags=["painel"])
def painel(db: Session = Depends(get_db), _=Depends(exigir(*STAFF))):
    wf.fechar_automaticamente(db)
    momento = agora()
    abertos = db.scalars(select(Pedido).where(Pedido.estado.in_(wf.ABERTOS))).all()
    estados_sla = [sla.estado_sla(p, momento) for p in abertos]
    por_tecnico: dict[str, int] = {}
    for p in abertos:
        if p.estado == "em_aprovacao":
            continue  # ainda não chegou ao Helpdesk
        chave = p.tecnico.nome if p.tecnico else "Sem técnico"
        por_tecnico[chave] = por_tecnico.get(chave, 0) + 1
    hoje = date.today()
    resolvidos_7d = db.scalar(select(func.count()).select_from(Pedido)
                              .where(Pedido.resolvido_em >= momento - timedelta(days=7)))
    eq_estado = dict(db.execute(select(Equipamento.estado, func.count()).group_by(Equipamento.estado)).all())
    garantia = db.scalars(select(Equipamento).where(Equipamento.estado != "abatido",
                                                    Equipamento.garantia_ate.between(hoje, hoje + timedelta(days=90)))
                          .order_by(Equipamento.garantia_ate)).all()
    licencas = [_licenca_out(l) for l in db.scalars(select(Licenca).order_by(Licenca.produto))]
    criticos = sorted((p for p, e in zip(abertos, estados_sla) if e in ("violado", "em_risco")),
                      key=lambda p: p.prazo_resolucao)
    return {
        "abertos": len(abertos),
        "por_estado": {e: sum(1 for p in abertos if p.estado == e) for e in wf.ABERTOS},
        "sem_tecnico": sum(1 for p in abertos if p.tecnico_id is None and p.estado != "em_aprovacao"),
        "sla_violado": estados_sla.count("violado"),
        "sla_em_risco": estados_sla.count("em_risco"),
        "resolvidos_7d": resolvidos_7d,
        "por_tecnico": [{"tecnico": k, "abertos": v} for k, v in sorted(por_tecnico.items(), key=lambda x: -x[1])],
        "atencao": [_resumo(p, momento) for p in criticos[:10]],
        "equipamentos_por_estado": {e: eq_estado.get(e, 0) for e in ("stock", "atribuido", "reparacao", "abatido")},
        "garantias_a_expirar": [{"etiqueta": e.etiqueta, "tipo": e.tipo, "modelo": e.modelo,
                                 "garantia_ate": e.garantia_ate} for e in garantia],
        "licencas": licencas,
        "licencas_a_renovar": [l for l in licencas if l["renovacao_em"]
                               and hoje <= l["renovacao_em"] <= hoje + timedelta(days=60)],
    }


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")
