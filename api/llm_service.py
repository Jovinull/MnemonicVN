"""Cliente unificado para o LM Studio com dois canais distintos:

- Chat (Maestro narrativo): qwen2.5-coder-7b-instruct via /v1/chat/completions
- Embedding (vetorização para pgvector): nomic-embed-text-v1.5.f32 via /v1/embeddings

Os dois clientes apontam para o mesmo servidor (localhost:1234) mas são instâncias
separadas para deixar explícito o papel de cada pipeline.
"""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from config import settings

# Cliente Chat — Maestro
chat_client = OpenAI(base_url=settings.LLM_BASE_URL, api_key=settings.LLM_API_KEY)

# Cliente Embedding — Nomic
embedding_client = OpenAI(base_url=settings.LLM_BASE_URL, api_key=settings.LLM_API_KEY)


def embed_text(text: str) -> list[float]:
    """Gera embedding de 768 dimensões via Nomic. Erra se a dimensão divergir."""
    resp = embedding_client.embeddings.create(
        model=settings.LLM_EMBEDDING_MODEL,
        input=text,
    )
    vector = resp.data[0].embedding
    if len(vector) != settings.EMBEDDING_DIM:
        raise ValueError(
            f"Dimensão de embedding inesperada: {len(vector)} != {settings.EMBEDDING_DIM}. "
            f"Verifique LLM_EMBEDDING_MODEL e EMBEDDING_DIM em .env."
        )
    return vector


def chat_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.8,
    max_tokens: int = 600,
) -> dict[str, Any]:
    """Chama o Qwen pedindo resposta em JSON. Faz fallback gracioso se o modelo
    devolver texto livre (alguns modelos locais não respeitam response_format)."""
    try:
        resp = chat_client.chat.completions.create(
            model=settings.LLM_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
    except Exception:
        # Modelos sem suporte a response_format
        resp = chat_client.chat.completions.create(
            model=settings.LLM_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    raw = resp.choices[0].message.content or ""
    return _parse_json_lenient(raw)


def _parse_json_lenient(raw: str) -> dict[str, Any]:
    """Tenta extrair um objeto JSON mesmo de respostas com texto extra."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    return {"fala": raw, "novo_humor": None, "acao": None}
