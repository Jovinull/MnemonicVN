# VividNexus API

Backend FastAPI que orquestra o Maestro narrativo (Qwen 2.5 via LM Studio) e a memória semântica (PostgreSQL + pgvector + Nomic embeddings).

## Setup

1. Suba um PostgreSQL com a extensão `pgvector` instalada:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
2. Suba o LM Studio em `localhost:1234` carregando dois modelos:
   - Chat: `qwen2.5-coder-7b-instruct`
   - Embedding: `nomic-embed-text-v1.5.f32` (768 dimensões)
3. Copie `.env.example` → `.env` e ajuste `DATABASE_URL`.
4. Instale dependências e rode:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

A API sobe em `http://localhost:8000`. Docs interativos em `/docs`.

## Rotas iniciais

- `POST /interact` — jogador fala com NPC; faz RAG em memórias passadas e devolve JSON estruturado.
- `POST /world-tick` — avança o relógio do mundo.
- `GET /get-npc-status/{id}` — snapshot do NPC (local, rotina ativa, últimas memórias).
- `POST /npcs`, `POST /locais` — CRUD mínimo para popular o banco.

## Pipeline de IA

Os dois canais são instâncias `OpenAI(...)` separadas em `llm_service.py` apontando para o mesmo LM Studio mas com modelos distintos — um deve formatar JSON narrativo, o outro só vetoriza.
