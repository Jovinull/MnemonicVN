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
from pydantic import BaseModel
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
from models import Jogador, NPC, Local, Rotina
from schemas import (
    InteractRequest,
    InteractResponse,
    JogadorRead,
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
    clima = (estado.clima if estado else "Ensolarado") or "Ensolarado"
    return {
        "tick_atual": tick,
        "hora_jogo": hora.strftime("%H:%M"),
        "clima": clima,
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
# /observe — narração reativa pelo Qwen como Narrador
# ============================================================
# Schemas mantidos inline pra evitar mexer em schemas.py nesta fase.
class ObserveRequest(BaseModel):
    local_id: int
    jogador_id: int = 1


class ObserveResponse(BaseModel):
    descricao: str


def _narracao_local_vazio(local: Local) -> str:
    return (
        f"{local.descricao} "
        "Você fica um instante em silêncio, ouvindo o ambiente. "
        "Não tem mais ninguém aqui."
    )


def _narracao_fallback(local: Local, npcs: list[NPC]) -> str:
    nomes = ", ".join(n.nome.split()[0] for n in npcs)
    return f"Você está em {local.nome}. {nomes} ocupam o espaço, cada um nas suas próprias coisas."


@app.post("/observe", response_model=ObserveResponse)
def observe(payload: ObserveRequest, db: Session = Depends(get_db)) -> ObserveResponse:
    local = db.get(Local, payload.local_id)
    if local is None:
        raise HTTPException(status_code=404, detail="Local não encontrado")

    npcs = list(
        db.scalars(
            select(NPC).where(NPC.local_atual_id == local.id).order_by(NPC.nome)
        ).all()
    )

    # Local vazio: descrição estática curta, sem queimar tokens de LLM.
    if not npcs:
        return ObserveResponse(descricao=_narracao_local_vazio(local))

    jogador = _get_or_create_jogador(db)
    perfil_resumido = _resumo_perfil(jogador.perfil_psicologico or {})

    from models import EstadoMundo
    estado = db.scalars(select(EstadoMundo).limit(1)).first()
    clima_atual = (estado.clima if estado else "Ensolarado") or "Ensolarado"

    npcs_brief = "\n".join(
        f"- {n.nome} (afeição {n.afeicao}/100, humor {n.humor_atual})"
        for n in npcs
    )

    system_prompt = (
        "Você é o NARRADOR de uma Visual Novel em pt-BR. Sua função é "
        "descrever, em 1 ou 2 parágrafos curtos (no máximo 4 frases no "
        "total), a atmosfera do local e a linguagem corporal dos NPCs "
        "presentes ao notarem a chegada do jogador.\n\n"
        f"LOCAL: {local.nome}. {local.descricao}\n\n"
        f"CLIMA ATUAL: {clima_atual}. Descreva como esse clima afeta a "
        "atmosfera do local — luz que entra pela janela, som de fundo, "
        "temperatura percebida, umidade — e deixe esses elementos "
        "interagirem com as ações dos NPCs presentes.\n\n"
        "PERFIL DO JOGADOR (lousa em branco pós-amnésia, ainda se "
        f"definindo): tons predominantes — {perfil_resumido}.\n\n"
        f"NPCS PRESENTES E AFEIÇÃO ATUAL (escala 0–100):\n{npcs_brief}\n\n"
        "REGRAS RÍGIDAS:\n"
        "1. SHOW, DON'T TELL. Você NUNCA cita afeição, humor, números ou "
        "perfil diretamente. Mostra as consequências através de gestos, "
        "olhares, postura, voz, respiração, distância física, ritmo da "
        "ação que o NPC já estava fazendo.\n"
        "2. Mapeamento implícito (use, não cite):\n"
        "   - Afeição alta (>70): contato visual, sorriso involuntário, "
        "aproximação, voz mais leve, pausa o que estava fazendo.\n"
        "   - Afeição média (30–70): olhar de relance, postura neutra, "
        "ações que continuam sem se acomodar ao jogador.\n"
        "   - Afeição baixa (<30): evita olhar, fecha a postura, foca "
        "exageradamente em outra coisa, voz curta, vira de costas.\n"
        "3. NÃO gere diálogo. Nenhuma fala entre aspas. Só narração em "
        "terceira pessoa, no presente do indicativo.\n"
        "4. Se houver mais de um NPC, dê uma frase distinta para cada um, "
        "respeitando a afeição individual.\n"
        "5. Tom literário, conciso. Evite clichês ('o ar está pesado', "
        "'o silêncio cortava a sala').\n\n"
        'Responda em JSON com EXATAMENTE uma chave: {"descricao": str}.'
    )
    user_prompt = (
        f"O jogador acaba de entrar em '{local.nome}' e olha em volta. "
        "Descreva o que ele vê e sente."
    )

    try:
        raw = chat_json(system_prompt, user_prompt, temperature=0.85, max_tokens=350)
        descricao = str(raw.get("descricao") or "").strip()
    except Exception:
        logger.exception("Falha no Narrador do /observe")
        descricao = ""

    if not descricao:
        descricao = _narracao_fallback(local, npcs)

    return ObserveResponse(descricao=descricao)


# ============================================================
# Helpers de afeição / perfil do jogador (hard state)
# ============================================================
CONTEXTO_JOGADOR = (
    "CONTEXTO DO JOGADOR: O jogador sofre de amnésia episódica "
    "irreversível após um acidente. Ele não lembra de NADA do seu "
    "passado. As memórias antigas foram deletadas. Sua personalidade "
    "atual é uma lousa em branco e está sendo moldada exclusivamente "
    "pelo que ele diz agora. Os NPCs lembram dele antes do acidente, "
    "mas devem reagir e se adaptar a quem ele está se tornando hoje. "
    "Avalie o tom e a intenção do jogador e responda de forma natural."
)


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _afeicao_modifier_text(score: int) -> str:
    """Tradução textual da escala 0–100 para o system prompt do Qwen."""
    if score > 70:
        return "Você é muito apegado a ele e tende a ser caloroso, paciente e protetor."
    if score < 30:
        return "Você é hostil ou frio com ele — desconfia, responde curto, mantém distância."
    return "Você é neutro ou cauteloso com ele — nem caloroso nem hostil, ainda em observação."


def _resumo_perfil(perfil: dict) -> str:
    if not perfil:
        return "ainda sem padrão definido (poucas interações registradas)"
    items = sorted(perfil.items(), key=lambda kv: -kv[1])[:3]
    return ", ".join(f"{nome.lower()} ({n}x)" for nome, n in items)


def _get_or_create_jogador(db: Session) -> Jogador:
    jogador = db.get(Jogador, 1)
    if jogador is None:
        jogador = Jogador(id=1, perfil_psicologico={})
        db.add(jogador)
        db.flush()
    return jogador


def _normalize_tom(raw_tom) -> str | None:
    """Normaliza o tom para uma única palavra capitalizada (ex.: 'Gentil')."""
    if not raw_tom:
        return None
    palavra = str(raw_tom).strip().split()[0] if str(raw_tom).strip() else ""
    palavra = "".join(c for c in palavra if c.isalpha() or c == "-")
    if not palavra:
        return None
    return palavra.capitalize()


# ============================================================
# /interact — motor de inferência dupla (hard + soft state)
# ============================================================
@app.post("/interact", response_model=InteractResponse)
def interact(payload: InteractRequest, db: Session = Depends(get_db)) -> InteractResponse:
    npc = db.get(NPC, payload.npc_id)
    if npc is None:
        raise HTTPException(status_code=404, detail="NPC não encontrado")

    jogador = _get_or_create_jogador(db)
    memorias = retrieve_relevant_context(db, npc.id, payload.player_input, top_k=5)
    contexto = format_context_for_prompt(memorias)

    afeicao_atual = npc.afeicao if npc.afeicao is not None else 50
    perfil_resumido = _resumo_perfil(jogador.perfil_psicologico or {})

    from models import EstadoMundo
    estado = db.scalars(select(EstadoMundo).limit(1)).first()
    clima_atual = (estado.clima if estado else "Ensolarado") or "Ensolarado"

    system_prompt = (
        f"Você é {npc.nome}, um NPC em uma Visual Novel.\n"
        f"{CONTEXTO_JOGADOR}\n\n"
        f"Personalidade: {npc.personalidade}\n"
        f"Humor atual: {npc.humor_atual}\n"
        f"Seu nível de afeição pelo jogador é {afeicao_atual}/100. "
        f"{_afeicao_modifier_text(afeicao_atual)}\n"
        f"O jogador tem se mostrado predominantemente: {perfil_resumido}.\n"
        f"O clima lá fora está: {clima_atual}. Incorpore reações sutis a "
        "esse clima na sua linguagem corporal se fizer sentido (encolher "
        "no frio, suspirar com o calor, tensão com tempestade, etc.).\n"
        f"Memórias relevantes:\n{contexto}\n\n"
        f"{payload.contexto_extra or ''}\n\n"
        "Responda SEMPRE em JSON com EXATAMENTE estas chaves:\n"
        '  "fala": string — sua resposta ao jogador, na sua voz.\n'
        '  "novo_humor": string|null — um de '
        "[neutro, feliz, triste, irritado, surpreso] ou null se mantiver.\n"
        '  "acao": string|null — uma ação física curta, ou null.\n'
        '  "mudanca_afeicao": int — INTEIRO entre -2 e +2, avaliando o '
        "tom e a intenção da fala atual do jogador.\n"
        '  "tom_jogador": string — UMA única palavra classificando o tom '
        "do jogador agora (ex.: Gentil, Frio, Curioso, Agressivo, "
        "Carinhoso, Honesto, Evasivo, Brincalhão)."
    )
    user_prompt = f'O jogador diz: "{payload.player_input}"'

    raw = chat_json(system_prompt, user_prompt)
    fala = str(raw.get("fala", "")).strip() or "..."
    novo_humor = raw.get("novo_humor")
    acao = raw.get("acao")

    # ---- Hard state: ajustar afeição do NPC ----
    try:
        delta = int(raw.get("mudanca_afeicao") or 0)
    except (TypeError, ValueError):
        delta = 0
    delta = _clamp(delta, -2, 2)
    npc.afeicao = _clamp(afeicao_atual + delta, 0, 100)

    # ---- Soft state: contador de tons no perfil do jogador ----
    tom = _normalize_tom(raw.get("tom_jogador"))
    if tom:
        # Reatribuir o dict força o SQLAlchemy a marcar o JSON como dirty.
        perfil = dict(jogador.perfil_psicologico or {})
        perfil[tom] = int(perfil.get(tom, 0)) + 1
        jogador.perfil_psicologico = perfil
        db.add(jogador)

    if novo_humor:
        npc.humor_atual = str(novo_humor)

    db.add(npc)
    db.commit()
    db.refresh(npc)

    save_memory(
        db,
        npc_id=npc.id,
        texto=f"Jogador: {payload.player_input}\n{npc.nome}: {fala}",
        tipo="conversa",
    )

    logger.info(
        "interact npc=%s afeicao=%s (%+d) tom=%s",
        npc.nome, npc.afeicao, delta, tom or "-",
    )

    return InteractResponse(
        npc_id=npc.id,
        fala=fala,
        novo_humor=novo_humor,
        acao=acao,
        mudanca_afeicao=delta,
        nova_afeicao=npc.afeicao,
        tom_jogador=tom,
        raw_json=raw,
    )


@app.get("/jogador", response_model=JogadorRead)
def get_jogador(db: Session = Depends(get_db)) -> Jogador:
    """Snapshot do hard state do protagonista — útil pra debug/HUD futuro."""
    return _get_or_create_jogador(db)


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
