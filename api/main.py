"""VividNexus API — Maestro de uma Visual Novel generativa.

Rotas:
- POST /interact      — jogador fala com um NPC; usa RAG + Qwen e persiste a memória.
- POST /world-tick    — avança o relógio do mundo manualmente; o scheduler
                        em background também o aciona automaticamente.
- GET  /get-npc-status/{npc_id} — snapshot do NPC com rotina ativa e memórias recentes.

Ao subir, um `BackgroundScheduler` (APScheduler) dispara
`world_engine.advance_world` a cada `WORLD_TICK_INTERVAL_SECONDS` segundos.
A cada tick, NPCs com rotina ativa para a hora de jogo são movidos para o
local correspondente; cada movimentação é logada no stdout.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal, get_db, init_db
from llm_service import chat_json
from memory_service import (
    format_context_for_prompt,
    retrieve_relevant_context,
    save_memory,
)
from models import NPC, Local, Rotina
from schemas import (
    InteractRequest,
    InteractResponse,
    LocalCreate,
    LocalRead,
    NPCCreate,
    NPCRead,
    NPCStatusResponse,
    RotinaRead,
    WorldTickRequest,
    WorldTickResponse,
)
from world_engine import advance_world, game_time_at_tick, time_in_window

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vividnexus")

app = FastAPI(title="VividNexus API", version="0.2.0")

# ============================================================
# Scheduler de mundo (APScheduler)
# ============================================================
_scheduler: BackgroundScheduler | None = None


def _scheduled_tick() -> None:
    """Job do APScheduler. Abre uma sessão própria — jobs não estão dentro
    do request lifecycle do FastAPI, então não usam `Depends(get_db)`."""
    db = SessionLocal()
    try:
        advance_world(db, delta_ticks=1)
    except Exception:
        logger.exception("Falha no tick automático do mundo")
    finally:
        db.close()


@app.on_event("startup")
def _startup() -> None:
    init_db()

    global _scheduler
    interval = settings.WORLD_TICK_INTERVAL_SECONDS
    if interval <= 0:
        logger.info("Scheduler do mundo desativado (WORLD_TICK_INTERVAL_SECONDS=0).")
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _scheduled_tick,
        trigger="interval",
        seconds=interval,
        id="world_tick",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler iniciado: tick a cada %ss (cada tick = %s minutos de jogo).",
        interval,
        settings.WORLD_MINUTES_PER_TICK,
    )


@app.on_event("shutdown")
def _shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler do mundo parado.")


# ============================================================
# Health / CRUD
# ============================================================
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/world-status")
def world_status(db: Session = Depends(get_db)) -> dict:
    """Snapshot leve do tempo de jogo. Usado pelo HUD do Ren'Py em cada
    iteração do main_loop — barato (apenas 1 SELECT, sem LLM)."""
    from models import EstadoMundo
    estado = db.scalars(select(EstadoMundo).limit(1)).first()
    tick = estado.tick_atual if estado else 0
    hora = game_time_at_tick(tick)
    return {
        "tick_atual": tick,
        "hora_jogo": hora.strftime("%H:%M"),
    }


@app.post("/npcs", response_model=NPCRead, status_code=201)
def create_npc(payload: NPCCreate, db: Session = Depends(get_db)) -> NPC:
    npc = NPC(**payload.model_dump())
    db.add(npc)
    db.commit()
    db.refresh(npc)
    return npc


@app.post("/locais", response_model=LocalRead, status_code=201)
def create_local(payload: LocalCreate, db: Session = Depends(get_db)) -> Local:
    local = Local(**payload.model_dump())
    db.add(local)
    db.commit()
    db.refresh(local)
    return local


@app.get("/locais", response_model=list[LocalRead])
def list_locais(db: Session = Depends(get_db)) -> list[Local]:
    return list(db.scalars(select(Local).order_by(Local.id)).all())


@app.get("/locais/{local_id}/npcs", response_model=list[NPCRead])
def npcs_no_local(local_id: int, db: Session = Depends(get_db)) -> list[NPC]:
    """Quais NPCs estão neste local agora? Usado pelo main_loop sandbox do Ren'Py."""
    if db.get(Local, local_id) is None:
        raise HTTPException(status_code=404, detail="Local não encontrado")
    stmt = select(NPC).where(NPC.local_atual_id == local_id).order_by(NPC.nome)
    return list(db.scalars(stmt).all())


# ============================================================
# /interact
# ============================================================
@app.post("/interact", response_model=InteractResponse)
def interact(payload: InteractRequest, db: Session = Depends(get_db)) -> InteractResponse:
    npc = db.get(NPC, payload.npc_id)
    if npc is None:
        raise HTTPException(status_code=404, detail="NPC não encontrado")

    memorias = retrieve_relevant_context(db, npc.id, payload.player_input, top_k=5)
    contexto = format_context_for_prompt(memorias)

    # Contexto global do protagonista — injetado em TODA interação para que
    # o NPC reaja à premissa da amnésia (ver Fase 7 do design doc).
    contexto_jogador = (
        "CONTEXTO DO JOGADOR: O jogador sofre de amnésia episódica "
        "irreversível após um acidente. Ele não lembra de NADA do seu "
        "passado. As memórias antigas foram deletadas. Sua personalidade "
        "atual é uma lousa em branco e está sendo moldada exclusivamente "
        "pelo que ele diz agora. Os NPCs lembram dele antes do acidente, "
        "mas devem reagir e se adaptar a quem ele está se tornando hoje. "
        "Avalie o tom e a intenção do jogador e responda de forma natural."
    )

    system_prompt = (
        f"Você é {npc.nome}, um NPC em uma Visual Novel.\n"
        f"{contexto_jogador}\n\n"
        f"Personalidade: {npc.personalidade}\n"
        f"Humor atual: {npc.humor_atual}\n"
        f"Memórias relevantes:\n{contexto}\n\n"
        f"{payload.contexto_extra or ''}\n\n"
        "Responda SEMPRE em JSON com as chaves: "
        '{"fala": str, "novo_humor": str|null, "acao": str|null}.'
    )
    user_prompt = f'O jogador diz: "{payload.player_input}"'

    raw = chat_json(system_prompt, user_prompt)
    fala = str(raw.get("fala", "")).strip() or "..."
    novo_humor = raw.get("novo_humor")
    acao = raw.get("acao")

    if novo_humor:
        npc.humor_atual = str(novo_humor)
        db.add(npc)
        db.commit()

    save_memory(
        db,
        npc_id=npc.id,
        texto=f"Jogador: {payload.player_input}\n{npc.nome}: {fala}",
        tipo="conversa",
    )

    return InteractResponse(
        npc_id=npc.id,
        fala=fala,
        novo_humor=novo_humor,
        acao=acao,
        raw_json=raw,
    )


# ============================================================
# /world-tick (manual)
# ============================================================
@app.post("/world-tick", response_model=WorldTickResponse)
def world_tick(payload: WorldTickRequest, db: Session = Depends(get_db)) -> WorldTickResponse:
    advance_world(db, delta_ticks=payload.delta_ticks)

    from models import EstadoMundo
    estado = db.scalars(select(EstadoMundo).limit(1)).first()
    return WorldTickResponse(
        tick_atual=estado.tick_atual,
        clima=estado.clima,
        eventos_globais_ativos=list(estado.eventos_globais_ativos or []),
        atualizado_em=estado.atualizado_em,
    )


# ============================================================
# /get-npc-status
# ============================================================
@app.get("/get-npc-status/{npc_id}", response_model=NPCStatusResponse)
def get_npc_status(npc_id: int, db: Session = Depends(get_db)) -> NPCStatusResponse:
    npc = db.get(NPC, npc_id)
    if npc is None:
        raise HTTPException(status_code=404, detail="NPC não encontrado")

    from models import EstadoMundo
    estado = db.scalars(select(EstadoMundo).limit(1)).first()
    tick = estado.tick_atual if estado else 0
    agora_jogo = game_time_at_tick(tick)

    rotina_atual = _rotina_em_curso(db, npc_id, agora_jogo)
    ultimas = _ultimas_memorias(db, npc_id, limit=5)

    return NPCStatusResponse(
        npc=NPCRead.model_validate(npc),
        local=LocalRead.model_validate(npc.local_atual) if npc.local_atual else None,
        rotina_atual=RotinaRead.model_validate(rotina_atual) if rotina_atual else None,
        ultimas_memorias=ultimas,
    )


def _rotina_em_curso(db: Session, npc_id: int, agora) -> Rotina | None:
    candidatas = db.scalars(select(Rotina).where(Rotina.npc_id == npc_id)).all()
    for r in candidatas:
        if time_in_window(agora, r.hora_inicio, r.hora_fim):
            return r
    return None


def _ultimas_memorias(db: Session, npc_id: int, limit: int = 5) -> list[str]:
    from models import Memoria

    stmt = (
        select(Memoria)
        .where(Memoria.npc_id == npc_id)
        .order_by(Memoria.timestamp.desc())
        .limit(limit)
    )
    return [m.texto_original for m in db.scalars(stmt).all()]


# ============================================================
# Entry point
# ============================================================
if __name__ == "__main__":
    import uvicorn

    # reload=False com APScheduler — o reloader cria 2 processos e o scheduler
    # rodaria duas vezes. Em dev, edite e mate manualmente, ou rode o uvicorn
    # CLI com --workers=1 e --reload se realmente quiser.
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=False)
