# screens_hud.rpy
# HUD minimalista do mundo: relógio + local atual.
# Mostrado em loop pelo main_loop e escondido nos encerramentos.
# Posicionado no canto superior direito; zorder alto pra ficar acima dos
# sprites mas abaixo do `api_thinking` (zorder 100) para não competir com
# o indicador de carregamento.

screen hud_mundo(hora_str, local_nome):
    zorder 90
    modal False
    tag hud  # garante que múltiplos shows substituam ao invés de empilhar

    # Decide o ícone com base na hora — sol durante o dia, lua à noite.
    # Parsing tolerante: se hora_str vier estranha, cai pro símbolo neutro.
    python:
        try:
            _hud_hour = int(hora_str.split(":")[0])
        except Exception:
            _hud_hour = 12
        _hud_icon = u"☀" if 6 <= _hud_hour < 18 else u"☾"  # ☀ / ☾

    frame:
        xalign 1.0
        yalign 0.0
        xoffset -24
        yoffset 24
        background Frame("#0008", 18, 18)
        padding (20, 12)

        vbox:
            spacing 4

            hbox:
                spacing 10
                yalign 0.5
                text "[_hud_icon!q]":
                    size 28
                    color "#ffe9a8" if 6 <= _hud_hour < 18 else "#cad6ff"
                text "[hora_str!q]":
                    size 28
                    color "#ffffff"

            text "[local_nome!q]":
                size 16
                color "#cccccc"
                xalign 0.0


# ============================================================
# Helper: aplica regras de roupa por janela horária
# ============================================================
init python:
    def aplicar_outfit_por_hora(hora_str):
        """Lê 'HH:MM' e ajusta as variáveis de outfit dos 3 NPCs.

        Janelas:
          07:00–13:59 → seifuku (Aria/Mei) | office (Sayuri)
          14:00–20:59 → casual  (Aria/Mei) | dress  (Sayuri)
          21:00–06:59 → pajama  (Aria/Mei) | casual (Sayuri)

        Os personagens já estão amarrados a essas variáveis via
        ConditionSwitch em characters.rpy — basta atribuir e o sprite
        atualiza no próximo render.
        """
        try:
            hh = int(hora_str.split(":")[0])
        except Exception:
            return

        if 7 <= hh < 14:
            store.aria_outfit = "seifuku"
            store.mei_outfit = "seifuku"
            store.sayuri_outfit = "office"
        elif 14 <= hh < 21:
            store.aria_outfit = "casual"
            store.mei_outfit = "casual"
            store.sayuri_outfit = "dress"
        else:
            # 21:00–06:59 (madrugada e noite)
            store.aria_outfit = "pajama"
            store.mei_outfit = "pajama"
            store.sayuri_outfit = "casual"
