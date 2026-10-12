"""Esquemas Pydantic de entrada e saída da API."""

from datetime import date, datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator

TipoCliente = Literal["particular", "empresa"]
Ramo = Literal[
    "Automóvel", "Saúde", "Vida", "Multirriscos",
    "Acidentes de Trabalho", "Viagem", "Responsabilidade Civil",
]
EstadoApolice = Literal["activa", "suspensa", "anulada", "expirada"]
EstadoSinistro = Literal["participado", "em_analise", "aprovado", "recusado", "pago"]
FaseOportunidade = Literal["prospeccao", "proposta", "negociacao", "ganha", "perdida"]
TipoActividade = Literal["chamada", "email", "reuniao", "nota", "tarefa"]


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class MediadorIn(_Base):
    codigo: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=2, max_length=150)
    email: str | None = None
    telefone: str | None = None
    comissao_pct: float = Field(0, ge=0, le=100)


class ClienteIn(_Base):
    tipo: TipoCliente
    nome: str = Field(min_length=2, max_length=200)
    nif: str = Field(min_length=5, max_length=20)
    email: str | None = None
    telefone: str | None = None
    provincia: str | None = None
    mediador_id: int | None = None


class ApoliceIn(_Base):
    numero: str = Field(min_length=1, max_length=30)
    cliente_id: int
    ramo: Ramo
    premio_anual: float = Field(ge=0)
    capital_seguro: float | None = Field(None, ge=0)
    data_inicio: date
    data_fim: date
    estado: EstadoApolice = "activa"

    @model_validator(mode="after")
    def _datas(self):
        if self.data_fim <= self.data_inicio:
            raise ValueError("data_fim tem de ser posterior a data_inicio")
        return self


class SinistroIn(_Base):
    numero: str = Field(min_length=1, max_length=30)
    apolice_id: int
    data_ocorrencia: date
    descricao: str = Field(min_length=3)
    valor_reclamado: float = Field(0, ge=0)
    valor_pago: float = Field(0, ge=0)
    estado: EstadoSinistro = "participado"


class OportunidadeIn(_Base):
    cliente_id: int
    titulo: str = Field(min_length=2, max_length=200)
    ramo: Ramo
    valor_estimado: float = Field(0, ge=0)
    fase: FaseOportunidade = "prospeccao"
    data_prevista: date | None = None


class ActividadeIn(_Base):
    cliente_id: int
    tipo: TipoActividade
    assunto: str = Field(min_length=2, max_length=200)
    descricao: str | None = None
    data: date = Field(default_factory=date.today)
    concluida: bool = False


def _update_of(model: type[BaseModel]) -> type[BaseModel]:
    """Versão de actualização parcial (PATCH): todos os campos opcionais."""
    fields = {
        # Mantém as restrições (ge, min_length...) no tipo interior e aceita None.
        name: (Optional[Annotated[f.annotation, *f.metadata]] if f.metadata else Optional[f.annotation], None)
        for name, f in model.model_fields.items()
    }
    return create_model(f"{model.__name__[:-2]}Update", __base__=_Base, **fields)


def _out_of(model: type[BaseModel], **extra) -> type[BaseModel]:
    return create_model(f"{model.__name__[:-2]}Out", __base__=model, id=(int, ...), **extra)


MediadorUpdate = _update_of(MediadorIn)
ClienteUpdate = _update_of(ClienteIn)
ApoliceUpdate = _update_of(ApoliceIn)
SinistroUpdate = _update_of(SinistroIn)
OportunidadeUpdate = _update_of(OportunidadeIn)
ActividadeUpdate = _update_of(ActividadeIn)

MediadorOut = _out_of(MediadorIn)
ClienteOut = _out_of(ClienteIn, criado_em=(datetime | None, None))
ApoliceOut = _out_of(ApoliceIn)
SinistroOut = _out_of(SinistroIn)
OportunidadeOut = _out_of(OportunidadeIn)
ActividadeOut = _out_of(ActividadeIn)


class ChatMensagem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatPedido(BaseModel):
    mensagens: list[ChatMensagem] = Field(min_length=1, max_length=20)


class ChatResposta(BaseModel):
    resposta: str
    accoes: list[dict]
