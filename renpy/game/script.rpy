# script.rpy
# Ponto de entrada da Visual Novel VividNexus.
# Este script é minimalista por design: a maioria das falas é gerada em runtime
# pela API (ver api_client.rpy). O fluxo aqui só serve para tirar a primeira
# foto dos três personagens iniciais e validar a comunicação com o backend.

# ---------- Aliases de background (cópias em images/backgrounds; brutos em ../source_assets/Backgrounds) ----------
image bg classroom = "backgrounds/Classroom_Day.png"
image bg hallway   = "backgrounds/School_Hallway_Day.png"
image bg cafeteria = "backgrounds/Cafeteria_Day.png"
image bg bedroom_aria = "backgrounds/Bedroom_Day.png"
image bg bedroom_mei  = "backgrounds/Bedroom_Evening.png"
image bg sayuri_apt   = "backgrounds/Sitting_Room.png"
image bg street       = "backgrounds/Street_Spring_Evening.png"
image bg train        = "backgrounds/Train_Evening.png"
image bg temple       = "backgrounds/Temple_Spring_Afternoon.png"

# ---------- IDs do banco (devem bater com o que o seed.py inseriu) ----------
default npc_id_aria   = 1
default npc_id_mei    = 2
default npc_id_sayuri = 3

default api_online = True
default api_error_msg = ""
default player_input = ""
default fala = ""
default novo_humor = None
default acao = None


# ============================================================
# Helper para conversar com qualquer NPC (assíncrono)
# ============================================================
# Dispara a chamada à API em uma thread daemon, mostra o indicador
# `api_thinking` e faz polling com `renpy.pause(hard=True)` — a thread chama
# `renpy.restart_interaction()` no fim, então o pause acorda imediatamente
# em vez de gastar o intervalo cheio.
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

    # Polling cooperativo. O hard=True garante que `renpy.restart_interaction`
    # consiga acordar este pause assim que a thread terminar.
    while not api_handle.done:
        $ renpy.pause(0.2, hard=True)

    hide screen api_thinking

    python:
        fala, novo_humor, acao = parse_interact_response(api_handle)
        apply_humor(npc_var_name, novo_humor)

    return


# ============================================================
# Início
# ============================================================
label start:

    # Sanity check da API
    python:
        try:
            api.health()
            api_online = True
            api_error_msg = ""
        except Exception as exc:
            api_online = False
            api_error_msg = str(exc)

    scene black with fade
    centered "VividNexus\n{size=-10}protótipo v0.1{/size}"
    with Pause(1.0)

    if not api_online:
        centered "{color=#f88}Backend offline — [api_error_msg]\nO jogo seguirá em modo fallback.{/color}"
        with Pause(2.0)

    # ----- Cena 1: sala de aula, encontro com Aria -----
    scene bg classroom with fade
    "Manhã. Sala 2-A. O sinal de início acabou de tocar."
    show aria_dynamic at center with dissolve

    aria "Ah — você é o aluno transferido, né? Tipo, todo mundo tá comentando."
    aria "Eu sou Aria. Aria Tanaka. Senta aí, sem cerimônia."

    menu:
        "O que você responde?"

        "Prazer, Aria. Pode me chamar pelo meu nome.":
            $ player_input = "Prazer, Aria. Pode me chamar pelo meu nome. Acabei de me transferir e ainda tô me localizando."
        "Comentando o quê, exatamente?":
            $ player_input = "Comentando o quê, exatamente? Não sei se é coisa boa ou ruim."
        "Você sempre fala tão rápido assim?":
            $ player_input = "Você sempre fala tão rápido assim? Mal consigo acompanhar."

    call _talk_to("aria", npc_id_aria, "Aria")
    show aria_dynamic at center with dissolve
    aria "[fala]"
    if acao:
        "({i}Aria [acao]{/i})"

    # ----- Cena 2: corredor, esbarrão com Mei -----
    scene bg hallway with fade
    "Intervalo. O corredor está cheio. Você quase tromba com alguém — uma menina de cabelo rosa, com um caderno apertado contra o peito."

    show mei_dynamic at center with dissolve
    mei "Ah — me desculpa, eu... não tava prestando atenção."

    menu:
        "Como reage?"

        "Tudo bem. O que você desenha?":
            $ player_input = "Tudo bem, foi mal eu também. Posso perguntar… o que você desenha nesse caderno?"
        "Você precisa de ajuda?":
            $ player_input = "Você tá bem? Parece meio perdida — precisa de ajuda?"
        "Não foi nada. Bom dia.":
            $ player_input = "Não foi nada. Bom dia."

    call _talk_to("mei", npc_id_mei, "Mei")
    show mei_dynamic at center with dissolve
    mei "[fala]"
    if acao:
        "({i}Mei [acao]{/i})"

    # ----- Cena 3: depois da aula, Sayuri chama -----
    scene bg classroom with fade
    "Fim do dia. A sala se esvazia. A professora Sayuri ergue os olhos do livro de chamada e te encara — calma, mas direta."

    show sayuri_dynamic at center with dissolve
    sayuri "Você. Pode ficar mais uns minutos? Não é nada grave — só quero te conhecer melhor."

    menu:
        "Você fica?"

        "Claro. Em que posso ajudar, professora?":
            $ player_input = "Claro, professora. Em que posso ajudar?"
        "Sobre o quê?":
            $ player_input = "Sobre o quê? Fiz alguma coisa errada?"
        "Tô meio cansado, mas tudo bem.":
            $ player_input = "Tô meio cansado, mas tudo bem. Pode falar."

    call _talk_to("sayuri", npc_id_sayuri, "Sayuri")
    show sayuri_dynamic at center with dissolve
    sayuri "[fala]"
    if acao:
        "({i}Sayuri [acao]{/i})"

    # ----- Encerramento -----
    scene bg street with fade
    "Final do dia. Você sai da escola, e a rua principal já tem aquele tom dourado de fim de tarde."
    "Três rostos, três conversas. O resto da história depende do que você fizer com elas."

    centered "{size=+5}— Fim do protótipo —{/size}\n{size=-5}continue construindo a partir daqui{/size}"
    return
