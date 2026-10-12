"""API e interface web do CRM MHAIS."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import agent, db as dbmod, schemas as s, seed, services
from .db import get_db
from .models import Actividade, Apolice, Cliente, Mediador, Oportunidade, Sinistro

load_dotenv()
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    dbmod.init_db()
    if os.getenv("CRM_SEED", "1") == "1":
        with dbmod.SessionLocal() as db:
            seed.carregar(db)
    yield


app = FastAPI(title="CRM MHAIS", version="0.1.0", lifespan=lifespan)


def _commit(db: Session, obj=None):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        msg = str(exc.orig).lower()
        if "unique" in msg:
            raise HTTPException(409, "Já existe um registo com esse identificador (número, código ou NIF).")
        if "foreign key" in msg:
            raise HTTPException(409, "Operação recusada: o registo tem dependências ou referencia um registo inexistente.")
        raise HTTPException(409, "Violação de integridade dos dados.")
    if obj is not None:
        db.refresh(obj)


def _validar_refs(db: Session, model, dados: dict):
    """Confirma que as chaves estrangeiras indicadas existem (mensagem clara em vez de erro SQL)."""
    for fk in model.__table__.foreign_keys:
        valor = dados.get(fk.parent.name)
        if valor is None:
            continue
        alvo = fk.column.table
        if db.execute(select(alvo.c.id).where(alvo.c.id == valor)).first() is None:
            raise HTTPException(422, f"{fk.parent.name}={valor} não existe.")


def crud(nome: str, model, entrada: type[BaseModel], update: type[BaseModel], saida: type[BaseModel],
         pesquisa: tuple[str, ...], filtros: tuple[str, ...], ordem) -> APIRouter:
    r = APIRouter(prefix=f"/api/{nome}", tags=[nome])

    @r.get("", response_model=list[saida])
    def listar(request: Request, q: str | None = None, limit: int = Query(200, le=1000), offset: int = 0,
               db: Session = Depends(get_db)):
        stmt = select(model)
        if q:
            stmt = stmt.where(or_(*(getattr(model, c).ilike(f"%{q}%") for c in pesquisa)))
        for f in filtros:
            if (v := request.query_params.get(f)) is not None:
                stmt = stmt.where(getattr(model, f) == v)
        return db.scalars(stmt.order_by(ordem).limit(limit).offset(offset)).all()

    @r.get("/{item_id}", response_model=saida)
    def obter(item_id: int, db: Session = Depends(get_db)):
        if (obj := db.get(model, item_id)) is None:
            raise HTTPException(404, "Registo não encontrado.")
        return obj

    @r.post("", response_model=saida, status_code=201)
    def criar(dados: entrada, db: Session = Depends(get_db)):  # type: ignore[valid-type]
        valores = dados.model_dump()
        _validar_refs(db, model, valores)
        obj = model(**valores)
        db.add(obj)
        _commit(db, obj)
        return obj

    @r.patch("/{item_id}", response_model=saida)
    def actualizar(item_id: int, dados: update, db: Session = Depends(get_db)):  # type: ignore[valid-type]
        if (obj := db.get(model, item_id)) is None:
            raise HTTPException(404, "Registo não encontrado.")
        alteracoes = dados.model_dump(exclude_unset=True)
        try:
            # Revalida o registo completo (ex.: data_fim > data_inicio após alteração parcial).
            entrada.model_validate({**saida.model_validate(obj).model_dump(), **alteracoes})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_url=False, include_context=False, include_input=False))
        _validar_refs(db, model, alteracoes)
        for k, v in alteracoes.items():
            setattr(obj, k, v)
        _commit(db, obj)
        return obj

    @r.delete("/{item_id}", status_code=204)
    def apagar(item_id: int, db: Session = Depends(get_db)):
        if (obj := db.get(model, item_id)) is None:
            raise HTTPException(404, "Registo não encontrado.")
        db.delete(obj)
        _commit(db)
        return Response(status_code=204)

    return r


for router in (
    crud("mediadores", Mediador, s.MediadorIn, s.MediadorUpdate, s.MediadorOut,
         ("nome", "codigo", "email"), (), Mediador.nome),
    crud("clientes", Cliente, s.ClienteIn, s.ClienteUpdate, s.ClienteOut,
         ("nome", "nif", "email", "telefone"), ("tipo", "provincia", "mediador_id"), Cliente.nome),
    crud("apolices", Apolice, s.ApoliceIn, s.ApoliceUpdate, s.ApoliceOut,
         ("numero", "ramo"), ("cliente_id", "ramo", "estado"), Apolice.data_fim),
    crud("sinistros", Sinistro, s.SinistroIn, s.SinistroUpdate, s.SinistroOut,
         ("numero", "descricao"), ("apolice_id", "estado"), Sinistro.data_ocorrencia.desc()),
    crud("oportunidades", Oportunidade, s.OportunidadeIn, s.OportunidadeUpdate, s.OportunidadeOut,
         ("titulo", "ramo"), ("cliente_id", "fase", "ramo"), Oportunidade.data_prevista),
    crud("actividades", Actividade, s.ActividadeIn, s.ActividadeUpdate, s.ActividadeOut,
         ("assunto", "descricao"), ("cliente_id", "tipo"), Actividade.data.desc()),
):
    app.include_router(router)


@app.get("/api/painel", tags=["painel"])
def painel(db: Session = Depends(get_db)):
    return services.painel(db)


@app.get("/api/renovacoes", tags=["painel"])
def renovacoes(dias: int = Query(60, ge=1, le=365), db: Session = Depends(get_db)):
    return services.renovacoes(db, dias)


@app.get("/api/clientes/{cliente_id}/360", tags=["clientes"])
def cliente_360(cliente_id: int, db: Session = Depends(get_db)):
    if (v := services.visao_cliente(db, cliente_id)) is None:
        raise HTTPException(404, "Cliente não encontrado.")
    return v


@app.post("/api/agente/chat", response_model=s.ChatResposta, tags=["agente"])
def agente_chat(pedido: s.ChatPedido, db: Session = Depends(get_db)):
    try:
        return agent.conversar(db, [m.model_dump() for m in pedido.mensagens])
    except agent.AgenteIndisponivel as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:  # erro do fornecedor do modelo (rede, quota, credenciais)
        raise HTTPException(502, f"Falha ao contactar o modelo de IA: {type(exc).__name__}")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")
