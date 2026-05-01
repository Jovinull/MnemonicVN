"""world_engine.py — motor de tempo do mundo.

Lógica:
- Cada `tick` avança `EstadoMundo.tick_atual` em 1.
- Tempo de jogo (hora do dia) = `WORLD_START_TIME` + (tick_atual * WORLD_MINUTES_PER_TICK), módulo 24h.
- Para cada NPC, encontra a `Rotina` cuja janela `[hora_inicio, hora_fim]` contém a hora
  atual e atualiza `npc.local_atual_id` se for diferente — registrando no log.

Observações:
- A hora de jogo é determinística a partir do tick — isso facilita testes.
- Janelas de rotina podem cruzar a meia-noite (ex.: 22:00–02:00). A função
  `time_in_window` cuida disso.
- O scheduler real (APScheduler) é configurado em `main.py`. Este módulo só
  expõe `advance_world(db, delta_ticks)` para que possa ser chamado tanto
  pelo scheduler quanto pelo endpoint manual `POST /world-tick`.
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, time, timedelta
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from memory_service import save_memory
from models import EstadoMundo, Local, NPC, Rotina

logger = logging.getLogger("world_engine")

# Climas suportados — a coluna `EstadoMundo.clima` é texto livre, mas só
# trocamos para um destes via roleta aleatória. Mantenha capitalizado pra
# combinar com o que vai pro HUD do jogador.
CLIMAS_POSSIVEIS = ["Ensolarado", "Nublado", "Chuva Leve", "Tempestade", "Vento Forte"]
CHANCE_MUDANCA_CLIMA = 0.15  # 15% por chamada de advance_world


class TickResult(NamedTuple):
    tick_atual: int
    hora_de_jogo: time
    movimentacoes: list[str]  # linhas de log "NPC X: Local A → Local B"


# ============================================================
# Tempo de jogo
# ============================================================
def _parse_start_time(raw: str) -> time:
    h, m = raw.strip().split(":")
    return time(int(h), int(m))


def game_time_at_tick(tick: int) -> time:
    base = _parse_start_time(settings.WORLD_START_TIME)
    delta = timedelta(minutes=tick * settings.WORLD_MINUTES_PER_TICK)
    # Ancora num datetime arbitrário só pra usar timedelta, depois descarta a data.
    anchor = datetime(2000, 1, 1, base.hour, base.minute)
    return (anchor + delta).time()


def time_in_window(now: time, inicio: time, fim: time) -> bool:
    """Aceita janelas que cruzam meia-noite (inicio > fim)."""
    if inicio <= fim:
        return inicio <= now <= fim
    return now >= inicio or now <= fim


# ============================================================
# Aplicação das rotinas
# ============================================================
def _rotina_ativa(db: Session, npc_id: int, agora: time) -> Rotina | None:
    candidatas = db.scalars(select(Rotina).where(Rotina.npc_id == npc_id)).all()
    for r in candidatas:
        if time_in_window(agora, r.hora_inicio, r.hora_fim):
            return r
    return None


def _ensure_estado(db: Session) -> EstadoMundo:
    estado = db.scalars(select(EstadoMundo).limit(1)).first()
    if estado is None:
        estado = EstadoMundo()
        db.add(estado)
        db.flush()
    return estado


def advance_world(db: Session, delta_ticks: int = 1) -> TickResult:
    """Avança `delta_ticks` ticks, move NPCs conforme rotina e devolve um resumo."""
    delta_ticks = max(1, int(delta_ticks))
    estado = _ensure_estado(db)
    estado.tick_atual = (estado.tick_atual or 0) + delta_ticks
    estado.atualizado_em = datetime.utcnow()

    # Roleta de clima — chance única por chamada. Para chamadas com
    # delta_ticks > 1 (raras, vindas do POST /world-tick manual), ainda só
    # rolamos uma vez para não spam-mudar o clima num tick só.
    if random.random() < CHANCE_MUDANCA_CLIMA:
        candidatos = [c for c in CLIMAS_POSSIVEIS if c.lower() != (estado.clima or "").lower()]
        if candidatos:
            novo_clima = random.choice(candidatos)
            antigo = estado.clima or "?"
            estado.clima = novo_clima
            logger.info(
                "[t=%s] O clima mudou: %s -> %s",
                estado.tick_atual, antigo, novo_clima,
            )

    agora = game_time_at_tick(estado.tick_atual)
    movimentacoes: list[str] = []

    npcs = db.scalars(select(NPC)).all()
    locais_por_id = {l.id: l for l in db.scalars(select(Local)).all()}

    for npc in npcs:
        rotina = _rotina_ativa(db, npc.id, agora)
        if rotina is None:
            continue

        if npc.local_atual_id == rotina.local_id:
            continue

        origem = locais_por_id.get(npc.local_atual_id)
        destino = locais_por_id.get(rotina.local_id)
        nome_origem = origem.nome if origem else "?"
        nome_destino = destino.nome if destino else "?"

        npc.local_atual_id = rotina.local_id
        linha = (
            f"[t={estado.tick_atual} | {agora.strftime('%H:%M')}] "
            f"{npc.nome}: {nome_origem} -> {nome_destino} "
            f"({rotina.acao_descrita})"
        )
        movimentacoes.append(linha)
        logger.info(linha)

        # Memória passiva — registra do ponto de vista do NPC. Falhas no
        # embedding (ex.: LM Studio offline) não devem derrubar o tick:
        # o movimento já foi aplicado, só perdemos o vetor desta entrada.
        memoria_texto = (
            f"São {agora.strftime('%H:%M')}. Fui para {nome_destino} "
            f"para {rotina.acao_descrita}"
        )
        try:
            save_memory(db, npc_id=npc.id, texto=memoria_texto, tipo="evento", relevancia=0.5)
        except Exception:
            logger.exception("Falha ao gerar memória passiva para %s", npc.nome)

    db.commit()
    db.refresh(estado)

    if not movimentacoes:
        logger.info(
            f"[t={estado.tick_atual} | {agora.strftime('%H:%M')}] "
            f"nenhuma movimentação."
        )

    return TickResult(
        tick_atual=estado.tick_atual,
        hora_de_jogo=agora,
        movimentacoes=movimentacoes,
    )
