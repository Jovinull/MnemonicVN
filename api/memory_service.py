"""Serviço de memória vetorial: salva memórias com embedding e busca por
similaridade no pgvector usando distância cosseno."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from llm_service import embed_text
from models import Memoria


def save_memory(
    db: Session,
    npc_id: int,
    texto: str,
    tipo: str = "conversa",
    relevancia: float = 1.0,
) -> Memoria:
    """Vetoriza o texto via Nomic e persiste como memória do NPC."""
    vector = embed_text(texto)
    memoria = Memoria(
        npc_id=npc_id,
        tipo=tipo,
        texto_original=texto,
        embedding=vector,
        timestamp=datetime.utcnow(),
        relevancia=relevancia,
    )
    db.add(memoria)
    db.commit()
    db.refresh(memoria)
    return memoria


def retrieve_relevant_context(
    db: Session,
    npc_id: int,
    query_text: str,
    top_k: int = 5,
) -> list[Memoria]:
    """Retorna as `top_k` memórias mais similares (cosseno) ao input atual.

    A coluna `embedding` é `pgvector.sqlalchemy.Vector`, que oferece
    `cosine_distance` / `l2_distance` / `max_inner_product` como métodos SQL.
    """
    query_vector = embed_text(query_text)

    stmt = (
        select(Memoria)
        .where(Memoria.npc_id == npc_id)
        .order_by(Memoria.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )
    return list(db.scalars(stmt).all())


def format_context_for_prompt(memorias: list[Memoria]) -> str:
    """Formata as memórias recuperadas para injeção no system prompt do Qwen."""
    if not memorias:
        return "(sem memórias relevantes)"
    linhas = []
    for m in memorias:
        ts = m.timestamp.strftime("%Y-%m-%d %H:%M")
        linhas.append(f"- [{ts} | {m.tipo}] {m.texto_original}")
    return "\n".join(linhas)
