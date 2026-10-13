"""Modelo de dados do Gestor de Pedidos DSI."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def agora() -> datetime:
    return datetime.now().replace(microsecond=0)


class Departamento(Base):
    __tablename__ = "departamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True)


class Utilizador(Base):
    __tablename__ = "utilizadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    departamento_id: Mapped[int | None] = mapped_column(ForeignKey("departamentos.id"))
    chefia_id: Mapped[int | None] = mapped_column(ForeignKey("utilizadores.id"))  # informativo (Entra ID)
    perfil: Mapped[str] = mapped_column(String(20), default="colaborador")  # colaborador|helpdesk|admin
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    entra_oid: Mapped[str | None] = mapped_column(String(36), unique=True)  # id do objecto no Entra ID

    departamento: Mapped[Departamento | None] = relationship()
    chefia: Mapped["Utilizador | None"] = relationship(remote_side=[id])


class ItemCatalogo(Base):
    __tablename__ = "catalogo"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    tipo: Mapped[str] = mapped_column(String(20))  # acesso|anywhere|equipamento|licenca|intervencao|outro
    descricao: Mapped[str | None] = mapped_column(String(200))  # ajuda curta mostrada no mosaico
    icone: Mapped[str] = mapped_column(String(20), default="caixa")
    ordem: Mapped[int] = mapped_column(Integer, default=100)
    requer_aprovacao: Mapped[bool] = mapped_column(Boolean, default=False)
    prioridade_padrao: Mapped[str] = mapped_column(String(10), default="media")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    campos: Mapped[str | None] = mapped_column(Text)  # formulário guiado (JSON, ver formularios.py)
    automacao: Mapped[str | None] = mapped_column(String(30))  # ver automacoes.py


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(20))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("catalogo.id"))
    prioridade: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(20), index=True)
    origem: Mapped[str] = mapped_column(String(10), default="portal")  # portal | email
    dados: Mapped[str | None] = mapped_column(Text)  # respostas ao formulário guiado (JSON)
    criado_por_id: Mapped[int] = mapped_column(ForeignKey("utilizadores.id"))
    beneficiario_id: Mapped[int] = mapped_column(ForeignKey("utilizadores.id"), index=True)
    tecnico_id: Mapped[int | None] = mapped_column(ForeignKey("utilizadores.id"), index=True)
    aprovador_id: Mapped[int | None] = mapped_column(ForeignKey("utilizadores.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    actualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    primeira_resposta_em: Mapped[datetime | None] = mapped_column(DateTime)
    resolvido_em: Mapped[datetime | None] = mapped_column(DateTime)
    fechado_em: Mapped[datetime | None] = mapped_column(DateTime)
    sla_inicio: Mapped[datetime] = mapped_column(DateTime, default=agora)  # recomeça após aprovação
    prazo_resposta: Mapped[datetime] = mapped_column(DateTime)
    prazo_resolucao: Mapped[datetime] = mapped_column(DateTime)

    item: Mapped[ItemCatalogo | None] = relationship()
    criado_por: Mapped[Utilizador] = relationship(foreign_keys=[criado_por_id])
    beneficiario: Mapped[Utilizador] = relationship(foreign_keys=[beneficiario_id])
    tecnico: Mapped[Utilizador | None] = relationship(foreign_keys=[tecnico_id])
    aprovador: Mapped[Utilizador | None] = relationship(foreign_keys=[aprovador_id])
    comentarios: Mapped[list["Comentario"]] = relationship(back_populates="pedido", order_by="Comentario.id")
    eventos: Mapped[list["Evento"]] = relationship(back_populates="pedido", order_by="Evento.id")

    @property
    def numero(self) -> str:
        return f"PED-{self.id:06d}"


class Comentario(Base):
    __tablename__ = "comentarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), index=True)
    autor_id: Mapped[int] = mapped_column(ForeignKey("utilizadores.id"))
    texto: Mapped[str] = mapped_column(Text)
    interno: Mapped[bool] = mapped_column(Boolean, default=False)  # só visível à DSI
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)

    pedido: Mapped[Pedido] = relationship(back_populates="comentarios")
    autor: Mapped[Utilizador] = relationship()


class Evento(Base):
    """Histórico (auditoria) de tudo o que acontece num pedido."""

    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), index=True)
    autor_id: Mapped[int | None] = mapped_column(ForeignKey("utilizadores.id"))
    accao: Mapped[str] = mapped_column(String(40))
    detalhe: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)

    pedido: Mapped[Pedido] = relationship(back_populates="eventos")
    autor: Mapped[Utilizador | None] = relationship()


class Equipamento(Base):
    __tablename__ = "equipamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    etiqueta: Mapped[str] = mapped_column(String(30), unique=True)
    tipo: Mapped[str] = mapped_column(String(30))
    marca: Mapped[str | None] = mapped_column(String(60))
    modelo: Mapped[str | None] = mapped_column(String(100))
    numero_serie: Mapped[str | None] = mapped_column(String(60), unique=True)
    estado: Mapped[str] = mapped_column(String(20), default="stock")  # stock|atribuido|reparacao|abatido
    utilizador_id: Mapped[int | None] = mapped_column(ForeignKey("utilizadores.id"), index=True)
    data_compra: Mapped[date | None] = mapped_column(Date)
    garantia_ate: Mapped[date | None] = mapped_column(Date)
    fornecedor: Mapped[str | None] = mapped_column(String(100))
    notas: Mapped[str | None] = mapped_column(Text)

    utilizador: Mapped[Utilizador | None] = relationship()


class Licenca(Base):
    __tablename__ = "licencas"

    id: Mapped[int] = mapped_column(primary_key=True)
    produto: Mapped[str] = mapped_column(String(120), unique=True)
    fornecedor: Mapped[str | None] = mapped_column(String(100))
    quantidade: Mapped[int] = mapped_column(Integer)
    custo_anual: Mapped[float | None] = mapped_column(Float)
    renovacao_em: Mapped[date | None] = mapped_column(Date)

    atribuicoes: Mapped[list["AtribuicaoLicenca"]] = relationship(back_populates="licenca", cascade="all, delete-orphan")


class AtribuicaoLicenca(Base):
    __tablename__ = "atribuicoes_licenca"
    __table_args__ = (UniqueConstraint("licenca_id", "utilizador_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    licenca_id: Mapped[int] = mapped_column(ForeignKey("licencas.id"), index=True)
    utilizador_id: Mapped[int] = mapped_column(ForeignKey("utilizadores.id"), index=True)
    atribuida_em: Mapped[date] = mapped_column(Date, default=date.today)

    licenca: Mapped[Licenca] = relationship(back_populates="atribuicoes")
    utilizador: Mapped[Utilizador] = relationship()


class Notificacao(Base):
    """Caixa de saída de emails: gravada na mesma transacção do pedido, enviada em segundo plano."""

    __tablename__ = "notificacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id"), index=True)
    para: Mapped[str] = mapped_column(String(150))
    assunto: Mapped[str] = mapped_column(String(250))
    corpo: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(12), default="pendente", index=True)  # pendente|enviada|simulada|erro
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
    erro: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    enviado_em: Mapped[datetime | None] = mapped_column(DateTime)


class MensagemRecebida(Base):
    """Emails da caixa do Helpdesk já processados (evita duplicar pedidos)."""

    __tablename__ = "mensagens_recebidas"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[str] = mapped_column(String(300), unique=True)
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id"))
    resultado: Mapped[str] = mapped_column(String(30))  # criado|comentario|ignorado
    remetente: Mapped[str | None] = mapped_column(String(150))
    recebido_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
