"""Modelo de dados do CRM, orientado ao negócio segurador."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Mediador(Base):
    __tablename__ = "mediadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(150))
    telefone: Mapped[str | None] = mapped_column(String(30))
    comissao_pct: Mapped[float] = mapped_column(Float, default=0)

    clientes: Mapped[list["Cliente"]] = relationship(back_populates="mediador")


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))  # particular | empresa
    nome: Mapped[str] = mapped_column(String(200), index=True)
    nif: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(150))
    telefone: Mapped[str | None] = mapped_column(String(30))
    provincia: Mapped[str | None] = mapped_column(String(50))
    mediador_id: Mapped[int | None] = mapped_column(ForeignKey("mediadores.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    mediador: Mapped[Mediador | None] = relationship(back_populates="clientes")
    apolices: Mapped[list["Apolice"]] = relationship(back_populates="cliente")
    oportunidades: Mapped[list["Oportunidade"]] = relationship(back_populates="cliente")
    actividades: Mapped[list["Actividade"]] = relationship(back_populates="cliente")


class Apolice(Base):
    __tablename__ = "apolices"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    ramo: Mapped[str] = mapped_column(String(40))
    premio_anual: Mapped[float] = mapped_column(Float)
    capital_seguro: Mapped[float | None] = mapped_column(Float)
    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date] = mapped_column(Date, index=True)
    estado: Mapped[str] = mapped_column(String(20), default="activa")

    cliente: Mapped[Cliente] = relationship(back_populates="apolices")
    sinistros: Mapped[list["Sinistro"]] = relationship(back_populates="apolice")


class Sinistro(Base):
    __tablename__ = "sinistros"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True)
    apolice_id: Mapped[int] = mapped_column(ForeignKey("apolices.id"), index=True)
    data_ocorrencia: Mapped[date] = mapped_column(Date)
    descricao: Mapped[str] = mapped_column(Text)
    valor_reclamado: Mapped[float] = mapped_column(Float, default=0)
    valor_pago: Mapped[float] = mapped_column(Float, default=0)
    estado: Mapped[str] = mapped_column(String(20), default="participado")

    apolice: Mapped[Apolice] = relationship(back_populates="sinistros")


class Oportunidade(Base):
    __tablename__ = "oportunidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    ramo: Mapped[str] = mapped_column(String(40))
    valor_estimado: Mapped[float] = mapped_column(Float, default=0)
    fase: Mapped[str] = mapped_column(String(20), default="prospeccao")
    data_prevista: Mapped[date | None] = mapped_column(Date)

    cliente: Mapped[Cliente] = relationship(back_populates="oportunidades")


class Actividade(Base):
    __tablename__ = "actividades"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    assunto: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)
    data: Mapped[date] = mapped_column(Date, default=date.today)
    concluida: Mapped[bool] = mapped_column(Boolean, default=False)

    cliente: Mapped[Cliente] = relationship(back_populates="actividades")
