# MnemonicVN — VividNexus

Visual Novel generativa: Ren'Py conversa com um backend FastAPI que orquestra
um LLM local (Qwen 2.5 via LM Studio) e uma memória semântica em PostgreSQL +
pgvector (embeddings via Nomic).

```
MnemonicVN/
├── api/                          # backend FastAPI + SQLAlchemy + pgvector
│   ├── main.py                   #   rotas /interact /world-tick /get-npc-status
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── llm_service.py            #   dois clientes OpenAI: Chat (Qwen) × Embed (Nomic)
│   ├── memory_service.py         #   save_memory / retrieve_relevant_context
│   ├── world_engine.py           #   advance_world: hora de jogo + movimento por rotina
│   ├── seed.py                   #   popula 3 NPCs + locais + rotinas + memórias
│   ├── manage.py                 #   CLI: run / init-db / reset-db / seed
│   ├── config.py
│   ├── requirements.txt
│   └── .env.example
└── renpy/
    ├── source_assets/            # backup dos PNGs brutos (backgrounds + sprite packs Sutemo) — não é lido pelo jogo
    └── game/
        ├── script.rpy            #   demo das três cenas iniciais
        ├── api_client.rpy        #   cliente HTTP async (AsyncRequest + restart_interaction)
        ├── screens_loading.rpy   #   indicador "[NPC] está pensando..."
        ├── characters.rpy        #   3 layeredimage + ConditionSwitch por humor
        ├── character_bible.md    #   personalidade detalhada dos 3 personagens
        ├── options.rpy
        └── images/
            ├── backgrounds/      #   88 PNGs (copiados de source_assets/Backgrounds)
            └── sprites/
                ├── bodies/       #   aria_body.png, mei_body.png, sayuri_body.png
                ├── hair/         #   um por personagem
                ├── heads/        #   <personagem>_head_<humor>.png (4 humores cada)
                └── outfits/      #   <personagem>_outfit_<estilo>.png (3 cada)
```

## Personagens iniciais

| ID | Nome             | Arquétipo            | Local inicial | Outfits                      |
|----|------------------|----------------------|---------------|------------------------------|
| 1  | Aria Tanaka      | A faísca extrovertida | Sala de Aula  | seifuku, casual, pajama      |
| 2  | Mei Kobayashi    | A observadora quieta  | Quarto de Mei | casual, seifuku, pajama      |
| 3  | Sayuri Hoshino   | A mentora calma       | Sala de Aula  | office, dress, casual        |

Personalidade completa, voz e gancho narrativo de cada um em
`renpy/game/character_bible.md`. Os mesmos textos (resumidos) vão
para a coluna `personalidade` no `POST /npcs` via o `seed.py`.

## Pré-requisitos

- Python 3.11+
- PostgreSQL 14+ com extensão `vector` (pgvector)
- LM Studio em `localhost:1234` com `qwen2.5-coder-7b-instruct` e `nomic-embed-text-v1.5.f32` carregados
- Ren'Py SDK 8+ (apontar o launcher para `renpy/`)

## Como rodar

### 1. PostgreSQL
Tenha um PostgreSQL 14+ rodando localmente com a extensão **pgvector**
disponível (no Windows, instaladores oficiais já trazem; em Linux, instale
o pacote `postgresql-XX-pgvector`). Não precisa criar o banco manualmente
— o `manage.py` faz isso. Só ajuste `DATABASE_URL` em `api/.env` (copie
de `.env.example`) com usuário e senha que tenham permissão de
`CREATE DATABASE`.

### 2. LM Studio
Abra o LM Studio, carregue os dois modelos e habilite o servidor local
(`Developer → Start Server`). Ele expõe `/v1/chat/completions` e
`/v1/embeddings` no mesmo endpoint.

### 3. Backend
```bash
cd api
pip install -r requirements.txt

python manage.py init-db   # cria banco vividnexus + extensão vector + tabelas
python manage.py seed      # popula 3 NPCs, 9 locais, 13 rotinas, 9 memórias
python manage.py run       # sobe em http://localhost:8000
```

Para limpar tudo e começar do zero:
```bash
python manage.py reset-db          # pede confirmação
python manage.py reset-db --yes    # sem confirmação
```

`manage.py` é o painel de controle do backend — todos os comandos abaixo
são equivalentes a passos manuais que você não precisa mais executar:

| Comando      | O que faz                                                     |
|--------------|---------------------------------------------------------------|
| `run`        | `uvicorn main:app` com `reload=False` (não duplica scheduler) |
| `init-db`    | `CREATE DATABASE` + `CREATE EXTENSION vector` + `create_all`  |
| `seed`       | popula NPCs, Locais, Rotinas, Memórias iniciais (idempotente) |
| `reset-db`   | dropa o banco inteiro, recria, e roda o seed                  |

### 4. Ren'Py
1. Abra o Ren'Py SDK launcher.
2. Aponte `Projects directory` para `MnemonicVN/`.
3. Selecione `renpy` e clique em *Launch Project*.

A demo abre na sala de aula, apresenta Aria, Mei e Sayuri em sequência,
chama `/interact` em cada cena e atualiza a expressão do sprite com base no
`novo_humor` que o Qwen retornar.

## Motor do mundo (auto-tick)

Ao subir o backend, um `BackgroundScheduler` (APScheduler) dispara
`world_engine.advance_world()` periodicamente. Cada tick:

1. Avança `EstadoMundo.tick_atual`.
2. Calcula a hora de jogo: `WORLD_START_TIME + tick * WORLD_MINUTES_PER_TICK`.
3. Para cada NPC, encontra a `Rotina` cuja janela contém a hora de jogo
   (suporta janelas que cruzam meia-noite) e atualiza `local_atual_id` se
   for diferente.
4. Cada movimentação é logada no stdout do uvicorn:
   ```
   [t=12 | 09:00] Aria Tanaka: Estação de Trem -> Sala de Aula (Aulas matinais...)
   ```

Configurável em `.env`:
- `WORLD_TICK_INTERVAL_SECONDS` — período do scheduler em segundos reais (0 desliga).
- `WORLD_MINUTES_PER_TICK` — quantos minutos de jogo cada tick avança.
- `WORLD_START_TIME` — hora de jogo no tick 0 (HH:MM).

`POST /world-tick` continua disponível para avanços manuais — é o mesmo
caminho de código (`advance_world`).

## Refatoração async no Ren'Py

`api_client.rpy` expõe `interact_async()` que devolve um `AsyncRequest`.
A label `_talk_to` no `script.rpy`:

1. Dispara a thread.
2. Mostra a screen `api_thinking` com pontinhos animados e contador de ms.
3. Faz polling com `renpy.pause(0.2, hard=True)` — a thread chama
   `renpy.restart_interaction()` no fim, então o pause acorda
   imediatamente em vez de esperar o intervalo cheio.
4. Lê `result`/`error` via `parse_interact_response()` e aplica o humor.

A UI do Ren'Py continua respondendo (menu/save/quit) mesmo enquanto o
Qwen demora vários segundos para responder.

## Pipeline de IA (resumo)

`llm_service.py` mantém **dois clientes `OpenAI` separados** apontando para
o mesmo LM Studio (`localhost:1234/v1`):

- **Chat** — modelo `qwen2.5-coder-7b-instruct`, `response_format=json_object`
  (com fallback de parse se o modelo não respeitar). System prompt é montado
  em `main.py:/interact` com `personalidade + humor_atual + memórias_relevantes + contexto_extra`.
- **Embedding** — modelo `nomic-embed-text-v1.5.f32`, valida 768 dimensões.
  Toda memória passa por aqui antes de virar `Vector(768)` no Postgres.
  Busca semântica usa `embedding.cosine_distance(vector)` em
  `memory_service.retrieve_relevant_context`.

## Próximos passos sugeridos

1. Adicionar índice `IVFFlat` ou `HNSW` na coluna `memorias.embedding`
   quando a base ultrapassar ~10k vetores.
2. Gerar memórias passivas no scheduler — quando um NPC se move por
   rotina, registrar uma "memória de evento" para ele (sem precisar de
   conversa com o jogador).
3. Adicionar um quarto humor (`surpreso`) — copiar o asset, adicionar
   `attribute surpreso:` no `layeredimage` e expandir o `ConditionSwitch`.
4. Persistir o estado do humor entre sessões do Ren'Py sincronizando com
   `GET /get-npc-status/{id}` no `start` (hoje ele recomeça em "neutro").

## Créditos e Agradecimentos (Assets)

### Sprites de Personagens
Arte original por **Sutemo** (Stereo-Mono).
- **Links de Apoio:** [Ko-fi](https://ko-fi.com/sutemo) | [DeviantArt](https://www.deviantart.com/stereo-mono)
- **Pacotes Utilizados:**
  - [Female Mature Anime Sprite (V1/V2)](https://sutemo.itch.io/female-mature-anime-sprite)
  - [Female Character Sprite (V1/V2)](https://sutemo.itch.io/female-character)
  - [Halfbody Female Character Sprite](https://sutemo.itch.io/halfbodyfemalesutemo)
  - [Male Character Sprite](https://sutemo.itch.io/male-character-sprite-for-visual-novel)
- **Licença (Sutemo):** Os sprites podem ser usados em projetos pessoais ou comerciais (jogos, vídeos, etc.). É proibida a revenda dos sprites por si só, incluindo a criação de criadores de personagens (character creators).

### Backgrounds (Cenários)
Arte original por **Noraneko Games** (Yumebackground).
- **Link do Projeto:** [Yumebackground Pack](https://noranekogames.itch.io/yumebackground)
- **Regras de Uso (Noraneko Games):**
  - O crédito a "Noraneko Games" é obrigatório e deve ser dado nos créditos do jogo, em um arquivo de texto acompanhando o jogo, ou na descrição de onde o jogo é baixado.
  - Os assets não podem ser revendidos sozinhos, dentro ou fora do jogo.
  - Não utilizar para glorificar pedofilia, homofobia, racismo ou ameaças a pessoas reais.
  - Uso comercial é permitido para jogos (desde que o usuário não tenha que comprar o background especificamente para vê-lo).
  - É permitida a modificação da imagem (mudar cores, desenhar por cima à mão, adicionar personagens), desde que as regras originais continuem sendo seguidas.
  - **RESTRIÇÃO ESTRITA DE IA:** Nenhum lançamento da Noraneko Games pode ser usado com IA de forma alguma (incluindo, mas não se limitando a treinamento, img2img, retoques, ou emparelhado com). *(Nota do desenvolvedor: Os cenários neste projeto são exibidos como arte final 2D estática e não interagem, alimentam ou são modificados pela IA generativa textual do projeto).*
