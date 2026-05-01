from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import relationship

from config import settings
from database import Base


class Local(Base):
    __tablename__ = "locais"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), unique=True, nullable=False, index=True)
    descricao = Column(Text, nullable=False, default="")
    coordenadas = Column(JSON, nullable=False, default=dict)  # {"x": 0, "y": 0, "z": 0}

    npcs = relationship("NPC", back_populates="local_atual")
    rotinas = relationship("Rotina", back_populates="local")


class NPC(Base):
    __tablename__ = "npcs"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), unique=True, nullable=False, index=True)
    personalidade = Column(Text, nullable=False, default="")
    atributos_base = Column(JSON, nullable=False, default=dict)  # ex.: {"forca": 5, "carisma": 7}
    local_atual_id = Column(Integer, ForeignKey("locais.id"), nullable=True)
    humor_atual = Column(String(60), nullable=False, default="neutro")

    local_atual = relationship("Local", back_populates="npcs")
    rotinas = relationship("Rotina", back_populates="npc", cascade="all, delete-orphan")
    memorias = relationship("Memoria", back_populates="npc", cascade="all, delete-orphan")


class Rotina(Base):
    __tablename__ = "rotinas"

    id = Column(Integer, primary_key=True, index=True)
    npc_id = Column(Integer, ForeignKey("npcs.id"), nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fim = Column(Time, nullable=False)
    local_id = Column(Integer, ForeignKey("locais.id"), nullable=False)
    acao_descrita = Column(Text, nullable=False, default="")

    npc = relationship("NPC", back_populates="rotinas")
    local = relationship("Local", back_populates="rotinas")


class Memoria(Base):
    __tablename__ = "memorias"

    id = Column(Integer, primary_key=True, index=True)
    npc_id = Column(Integer, ForeignKey("npcs.id"), nullable=False, index=True)
    tipo = Column(String(40), nullable=False, default="conversa")  # conversa | evento | reflexao
    texto_original = Column(Text, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    relevancia = Column(Float, nullable=False, default=1.0)

    npc = relationship("NPC", back_populates="memorias")


class EstadoMundo(Base):
    __tablename__ = "estado_mundo"

    id = Column(Integer, primary_key=True, index=True)
    tick_atual = Column(Integer, nullable=False, default=0)
    clima = Column(String(60), nullable=False, default="ensolarado")
    eventos_globais_ativos = Column(JSON, nullable=False, default=list)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
