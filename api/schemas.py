from datetime import datetime, time
from typing import Any

from pydantic import BaseModel, Field


# ---------- NPC ----------
class NPCBase(BaseModel):
    nome: str
    personalidade: str = ""
    atributos_base: dict[str, Any] = Field(default_factory=dict)
    local_atual_id: int | None = None
    humor_atual: str = "neutro"
    afeicao: int = 50
    conhece_jogador: bool = True


class NPCCreate(NPCBase):
    pass


class NPCRead(NPCBase):
    id: int

    class Config:
        from_attributes = True


# ---------- Local ----------
class LocalBase(BaseModel):
    nome: str
    descricao: str = ""
    coordenadas: dict[str, float] = Field(default_factory=dict)


class LocalCreate(LocalBase):
    pass


class LocalRead(LocalBase):
    id: int

    class Config:
        from_attributes = True


# ---------- Rotina ----------
class RotinaBase(BaseModel):
    npc_id: int
    hora_inicio: time
    hora_fim: time
    local_id: int
    acao_descrita: str = ""


class RotinaCreate(RotinaBase):
    pass


class RotinaRead(RotinaBase):
    id: int

    class Config:
        from_attributes = True


# ---------- Interação ----------
class InteractRequest(BaseModel):
    npc_id: int
    player_input: str
    contexto_extra: str | None = None


class InteractResponse(BaseModel):
    npc_id: int
    fala: str
    novo_humor: str | None = None
    acao: str | None = None
    mudanca_afeicao: int = 0
    nova_afeicao: int = 50
    tom_jogador: str | None = None
    raw_json: dict[str, Any]


# ---------- Jogador ----------
class JogadorRead(BaseModel):
    id: int
    perfil_psicologico: dict[str, int] = Field(default_factory=dict)

    class Config:
        from_attributes = True


# ---------- Tick / Mundo ----------
class WorldTickRequest(BaseModel):
    delta_ticks: int = 1


class WorldTickResponse(BaseModel):
    tick_atual: int
    clima: str
    eventos_globais_ativos: list[Any]
    atualizado_em: datetime


# ---------- Status NPC ----------
class NPCStatusResponse(BaseModel):
    npc: NPCRead
    local: LocalRead | None
    rotina_atual: RotinaRead | None
    ultimas_memorias: list[str]
