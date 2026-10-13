"""Esquemas de entrada e saída da API."""

from datetime import date, datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model

Perfil = Literal["colaborador", "helpdesk", "admin"]
TipoPedido = Literal["acesso", "anywhere", "equipamento", "licenca", "intervencao", "outro"]
Prioridade = Literal["critica", "alta", "media", "baixa"]
EstadoEquipamento = Literal["stock", "atribuido", "reparacao", "abatido"]


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class DepartamentoIn(_Base):
    nome: str = Field(min_length=2, max_length=100)


class UtilizadorIn(_Base):
    nome: str = Field(min_length=2, max_length=150)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=150)
    departamento_id: int | None = None
    chefia_id: int | None = None
    perfil: Perfil = "colaborador"
    activo: bool = True


class ItemCatalogoIn(_Base):
    nome: str = Field(min_length=2, max_length=150)
    tipo: TipoPedido
    descricao: str | None = Field(None, max_length=200)
    icone: str = Field("caixa", max_length=20)
    ordem: int = 100
    requer_aprovacao: bool = False
    prioridade_padrao: Prioridade = "media"
    activo: bool = True


class EquipamentoIn(_Base):
    etiqueta: str = Field(min_length=1, max_length=30)
    tipo: str = Field(min_length=2, max_length=30)
    marca: str | None = None
    modelo: str | None = None
    numero_serie: str | None = None
    estado: EstadoEquipamento = "stock"
    utilizador_id: int | None = None
    data_compra: date | None = None
    garantia_ate: date | None = None
    fornecedor: str | None = None
    notas: str | None = None


class LicencaIn(_Base):
    produto: str = Field(min_length=2, max_length=120)
    fornecedor: str | None = None
    quantidade: int = Field(ge=0)
    custo_anual: float | None = Field(None, ge=0)
    renovacao_em: date | None = None


def _update_of(model: type[BaseModel]) -> type[BaseModel]:
    fields = {
        name: (Optional[Annotated[f.annotation, *f.metadata]] if f.metadata else Optional[f.annotation], None)
        for name, f in model.model_fields.items()
    }
    return create_model(f"{model.__name__[:-2]}Update", __base__=_Base, **fields)


def _out_of(model: type[BaseModel], **extra) -> type[BaseModel]:
    return create_model(f"{model.__name__[:-2]}Out", __base__=model, id=(int, ...), **extra)


DepartamentoUpdate, DepartamentoOut = _update_of(DepartamentoIn), _out_of(DepartamentoIn)
UtilizadorUpdate, UtilizadorOut = _update_of(UtilizadorIn), _out_of(UtilizadorIn)
ItemCatalogoUpdate, ItemCatalogoOut = _update_of(ItemCatalogoIn), _out_of(ItemCatalogoIn)
EquipamentoUpdate, EquipamentoOut = _update_of(EquipamentoIn), _out_of(EquipamentoIn)
LicencaUpdate = _update_of(LicencaIn)
LicencaOut = _out_of(LicencaIn, usadas=(int, 0), livres=(int, 0))


class PedidoIn(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    descricao: str = Field(min_length=3, max_length=5000)
    beneficiario_id: int | None = None
    item_id: int | None = None
    tipo: TipoPedido | None = None
    prioridade: Prioridade | None = None


class PedidoResumo(BaseModel):
    id: int
    numero: str
    titulo: str
    tipo: str
    item: str | None
    prioridade: str
    estado: str
    beneficiario: str
    criado_por: str
    tecnico: str | None
    criado_em: datetime
    actualizado_em: datetime
    prazo_resolucao: datetime
    sla: str
    origem: str = "portal"


class ComentarioIn(BaseModel):
    texto: str = Field(min_length=1, max_length=5000)
    interno: bool = False


class AccaoIn(BaseModel):
    motivo: str | None = Field(None, max_length=5000)
    tecnico_id: int | None = None
    prioridade: Prioridade | None = None
    equipamento_id: int | None = None
    licenca_id: int | None = None


class LoginIn(BaseModel):
    utilizador_id: int
