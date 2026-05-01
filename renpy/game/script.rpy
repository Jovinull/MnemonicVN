# script.rpy
# VividNexus — loop sandbox.
#
# Estrutura:
#   start                : sanity check + sincronização inicial dos humores
#   intro                : narração curta de abertura
#   main_loop            : explorar locais, ver quem está lá, falar ou observar
#   _talk_to(...)        : chamada async ao backend (declarada mais abaixo)
#   _talk_with_<persona> : seleção de prompt específico de cada personagem

# ============================================================
# Aliases de background
# ============================================================
image bg classroom    = "backgrounds/Classroom_Day.png"
image bg hallway      = "backgrounds/School_Hallway_Day.png"
image bg cafeteria    = "backgrounds/Cafeteria_Day.png"
image bg bedroom_aria = "backgrounds/Bedroom_Day.png"
image bg bedroom_mei  = "backgrounds/Bedroom_Evening.png"
image bg sayuri_apt   = "backgrounds/Sitting_Room.png"
image bg street       = "backgrounds/Street_Spring_Evening.png"
image bg train        = "backgrounds/Train_Evening.png"
image bg temple       = "backgrounds/Temple_Spring_Afternoon.png"
image bg fallback     = "backgrounds/Street_Spring_Day.png"


# ============================================================
# Tabelas estáticas — mapeiam dados do backend para recursos do Ren'Py
# ============================================================
init python:
    # Nome do local (no banco) → alias de background do Ren'Py
    LOCAL_BG = {
        "Sala de Aula":           "bg classroom",
        "Corredor da Escola":     "bg hallway",
        "Cafeteria":              "bg cafeteria",
        "Quarto de Aria":         "bg bedroom_aria",
        "Quarto de Mei":          "bg bedroom_mei",
        "Apartamento de Sayuri":  "bg sayuri_apt",
        "Rua Principal":          "bg street",
        "Estação de Trem":        "bg train",
        "Templo":                 "bg temple",
    }

    # Nome do NPC (no banco) → chave usada por apply_humor + sprite dinâmico
    NPC_KEYS = {
        "Aria Tanaka":    ("aria",   "aria_dynamic"),
        "Mei Kobayashi":  ("mei",    "mei_dynamic"),
        "Sayuri Hoshino": ("sayuri", "sayuri_dynamic"),
    }

    POS_TRES = {0: (0.25, 1.0), 1: (0.50, 1.0), 2: (0.75, 1.0)}

    def bg_alias_for_local(nome_local):
        return LOCAL_BG.get(nome_local, "bg fallback")


# ============================================================
# Estado de jogo
# ============================================================
default npc_id_aria   = 1
default npc_id_mei    = 2
default npc_id_sayuri = 3

default api_online = True
default api_error_msg = ""

default player_input = ""
default fala = ""
default novo_humor = None
default acao = None

# Loop sandbox
default locais_cache = []         # lista de dicts vinda de GET /locais
default local_jogador_id = None   # int — ID do local em que o jogador está
default local_jogador_nome = ""   # nome do local em que o jogador está
default npcs_presentes = []       # lista de dicts {id, nome, humor_atual, ...}
default tick_atual_jogo = 0
default hora_jogo = "06:00"       # HH:MM da hora de jogo atual


# ============================================================
# Helper assíncrono — fala com qualquer NPC via /interact
# ============================================================
label _talk_to(npc_var_name, npc_id, speaker_name=None):
    if not api_online:
        python:
            fala = "(modo offline) Hmm... me conta mais."
            novo_humor = None
            acao = None
        return

    python:
        api_handle = api.interact_async(npc_id=npc_id, player_input=player_input)

    show screen api_thinking(speaker=speaker_name, handle=api_handle)

    while not api_handle.done:
        $ renpy.pause(0.2, hard=True)

    hide screen api_thinking

    python:
        fala, novo_humor, acao = parse_interact_response(api_handle)
        apply_humor(npc_var_name, novo_humor)
    return


# ============================================================
# Sub-labels: seleção de prompt + interação por personagem
# Cada personagem tem 3 prompts coerentes com sua voz; depois delega
# para `_talk_to` e exibe a fala com o `Character` correspondente.
# ============================================================
label _talk_with_aria:
    menu:
        "O que você diz pra Aria?"
        "Como foi o seu dia?":
            $ player_input = "Como foi o seu dia, Aria?"
        "Pensei em correr com você um dia desses.":
            $ player_input = "Pensei em correr com você um dia desses. Aceita?"
        "Você parece estranha hoje.":
            $ player_input = "Você parece estranha hoje. Aconteceu alguma coisa?"
        "Esquece, depois a gente fala.":
            return

    call _talk_to("aria", npc_id_aria, "Aria")
    aria "[fala]"
    if acao:
        "({i}Aria [acao]{/i})"
    return


label _talk_with_mei:
    menu:
        "O que você diz pra Mei?"
        "O que você está desenhando hoje?":
            $ player_input = "O que você está desenhando hoje? Não precisa mostrar se não quiser."
        "Posso sentar do seu lado?":
            $ player_input = "Posso sentar do seu lado? Em silêncio também tá bom."
        "Como você está se sentindo?":
            $ player_input = "Como você está se sentindo? De verdade."
        "Não vou te incomodar, foi mal.":
            return

    call _talk_to("mei", npc_id_mei, "Mei")
    mei "[fala]"
    if acao:
        "({i}Mei [acao]{/i})"
    return


# ============================================================
# Observação dinâmica do ambiente — narrador via /observe
# ============================================================
# Mostra a screen `api_observing` enquanto a thread de /observe roda,
# então exibe a descrição como narração padrão (sem speaker).

label _observar:
    if not api_online:
        "Você fica em silêncio um instante, só olhando ao redor."
        return

    python:
        obs_handle = api.observe_async(local_jogador_id)

    show screen api_observing(handle=obs_handle)

    while not obs_handle.done:
        $ renpy.pause(0.2, hard=True)

    hide screen api_observing

    $ obs_descricao = parse_observe_response(obs_handle)
    "[obs_descricao]"
    return


# Screen de loading dedicada ao /observe — reaproveita o transform
# `thinking_dots` definido em screens_loading.rpy.
screen api_observing(handle=None):
    zorder 100
    modal False
    tag thinking

    frame:
        xalign 0.5
        yalign 0.92
        background "#000000a0"
        padding (24, 12)

        hbox:
            spacing 12
            text "Observando o ambiente":
                color "#ffffff"
                size 22
            text "...":
                color "#ffffff"
                size 22
                at thinking_dots
            if handle is not None:
                text "([handle.elapsed_ms()] ms)":
                    color "#aaaaaa"
                    size 16


label _talk_with_sayuri:
    menu:
        "O que você diz pra Sayuri?"
        "Tem um minuto pra mim, professora?":
            $ player_input = "Tem um minuto pra mim, professora?"
        "Posso te perguntar uma coisa pessoal?":
            $ player_input = "Posso te perguntar uma coisa pessoal? Pode dizer não."
        "Tô preso num problema. Me ajuda a pensar?":
            $ player_input = "Tô preso num problema. Me ajuda a pensar?"
        "Depois eu volto.":
            return

    call _talk_to("sayuri", npc_id_sayuri, "Sayuri")
    sayuri "[fala]"
    if acao:
        "({i}Sayuri [acao]{/i})"
    return


# ============================================================
# Helpers de loop (Python)
# ============================================================
init python:
    def _sync_initial_humors():
        """Lê o humor atual de cada NPC do banco e atualiza o sprite local.
        Garante que sessões abertas dias depois carreguem o humor real."""
        if not api_online:
            return
        for npc_id, key in (
            (store.npc_id_aria,   "aria"),
            (store.npc_id_mei,    "mei"),
            (store.npc_id_sayuri, "sayuri"),
        ):
            try:
                status = api.get_npc_status(npc_id)
                npc_data = status.get("npc") if isinstance(status, dict) else None
                if npc_data:
                    apply_humor(key, npc_data.get("humor_atual"))
            except Exception:
                # Banco vazio ou backend instável — segue com o default.
                pass

    def _refresh_locais():
        try:
            store.locais_cache = api.list_locais() or []
        except Exception:
            store.locais_cache = []

    def _set_local_jogador(local):
        """`local` é um dict {id, nome, ...} vindo de /locais."""
        store.local_jogador_id = local["id"]
        store.local_jogador_nome = local["nome"]

    def _refresh_presentes():
        if store.local_jogador_id is None:
            store.npcs_presentes = []
            return
        try:
            store.npcs_presentes = api.npcs_no_local(store.local_jogador_id) or []
        except Exception:
            store.npcs_presentes = []

    def _initial_local():
        """Escolhe um local de partida razoável: 'Sala de Aula' se existir,
        senão o primeiro da lista."""
        for l in store.locais_cache:
            if l["nome"] == "Sala de Aula":
                return l
        return store.locais_cache[0] if store.locais_cache else None


# ============================================================
# Início
# ============================================================
label start:
    python:
        try:
            api.health()
            api_online = True
            api_error_msg = ""
        except Exception as exc:
            api_online = False
            api_error_msg = str(exc)

    scene black with fade
    centered "VividNexus\n{size=-10}protótipo sandbox v0.3{/size}"
    with Pause(1.0)

    if not api_online:
        centered "{color=#f88}Backend offline — [api_error_msg]\nO jogo seguirá em modo fallback.{/color}"
        with Pause(2.0)
        # Sem locais nem NPCs sincronizados não dá pra rodar o sandbox.
        jump end_offline

    # Sincronização inicial: humores reais + lista de locais
    $ _sync_initial_humors()
    $ _refresh_locais()
    $ inicial = _initial_local()
    if inicial is None:
        centered "{color=#f88}Banco vazio: rode `python manage.py seed`.{/color}"
        with Pause(3.0)
        jump end_offline
    $ _set_local_jogador(inicial)

    jump intro


label intro:
    $ _bg = bg_alias_for_local(local_jogador_nome)
    scene expression _bg with fade
    "Os médicos chamaram de Amnésia Retrógrada Episódica. Um nome chique para dizer que o 'você' de antes do acidente foi deletado para sempre."
    "Você sabe ler, fazer contas, sabe que o céu é azul. Mas não sabe quem amou, quem odiou, nem por que voltou para esta cidade."
    "Essas pessoas conhecem um fantasma com o seu rosto. Seu trabalho agora não é lembrar do passado... é decidir quem você vai ser daqui pra frente."
    jump main_loop


# ============================================================
# Main Loop — sandbox
# ============================================================
label main_loop:

    # ---- Snapshot do mundo ----
    # /world-status é barato (1 SELECT, sem LLM), seguro chamar sync.
    python:
        try:
            ws = api.get_world_status() or {}
            hora_jogo = ws.get("hora_jogo", hora_jogo)
            tick_atual_jogo = ws.get("tick_atual", tick_atual_jogo)
        except Exception:
            pass
        # Reflete a hora do mundo nas roupas dos 3 NPCs antes do render.
        aplicar_outfit_por_hora(hora_jogo)

    # HUD do relógio + local
    show screen hud_mundo(hora_jogo, local_jogador_nome)

    # Atualiza presença ANTES de desenhar a cena. Isso reflete imediatamente
    # qualquer movimentação automática feita pelo scheduler do mundo.
    $ _refresh_presentes()

    # Cenário do local atual
    $ _bg = bg_alias_for_local(local_jogador_nome)
    scene expression _bg with fade

    # Sprites dos NPCs presentes — até 3 posições fixas (esquerda/centro/direita)
    python:
        for idx, npc in enumerate(npcs_presentes[:3]):
            info = NPC_KEYS.get(npc["nome"])
            if not info:
                continue
            sprite = info[1]
            xpos, ypos = POS_TRES[idx]
            xform = Transform(xpos=xpos, xanchor=0.5, ypos=ypos, yanchor=1.0)
            renpy.show(sprite, at_list=[xform])

    # (a narração de quem está aqui agora vem dinamicamente do /observe,
    # acionado pela escolha "Apenas observar" no menu)

    # ---- Menu principal ----
    $ destinos = [l for l in locais_cache if l["id"] != local_jogador_id]
    $ falaveis = [n for n in npcs_presentes if n["nome"] in NPC_KEYS]

    menu:
        "O que fazer?"

        "Falar com Aria" if any(n["nome"] == "Aria Tanaka" for n in falaveis):
            call _talk_with_aria
            jump main_loop

        "Falar com Mei" if any(n["nome"] == "Mei Kobayashi" for n in falaveis):
            call _talk_with_mei
            jump main_loop

        "Falar com Sayuri" if any(n["nome"] == "Sayuri Hoshino" for n in falaveis):
            call _talk_with_sayuri
            jump main_loop

        "Apenas observar":
            call _observar
            jump main_loop

        "Ir para outro lugar...":
            call screen choose_destino(destinos)
            if _return is not None:
                $ _set_local_jogador(_return)
                $ tick_result = api.world_tick(delta_ticks=1) if api_online else None
                if tick_result:
                    $ tick_atual_jogo = tick_result.get("tick_atual", tick_atual_jogo)
            jump main_loop

        "Encerrar o dia":
            jump end_day


# Screen para escolher destino — mais bonito que um menu textual longo
screen choose_destino(destinos):
    modal True
    frame:
        xalign 0.5
        yalign 0.5
        background "#000000c0"
        padding (40, 30)

        vbox:
            spacing 12
            text "Para onde ir?" size 28 color "#ffffff"
            null height 8

            for loc in destinos:
                textbutton "[loc[nome]]":
                    action Return(loc)
                    text_size 22

            null height 8
            textbutton "Cancelar":
                action Return(None)
                text_size 20
                text_color "#aaaaaa"


# ============================================================
# Encerramentos
# ============================================================
label end_day:
    hide screen hud_mundo
    scene bg street with fade
    "Final do dia. As luzes da rua principal já estão acesas."
    "Você decide voltar pra casa. Amanhã tem mais."
    centered "{size=+5}— Fim do dia —{/size}"
    return


label end_offline:
    hide screen hud_mundo
    scene black with fade
    centered "Sem backend, sem mundo.\nSuba o backend e rode `python manage.py seed`."
    return
