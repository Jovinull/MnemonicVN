# screens_loading.rpy
# Indicador visual exibido enquanto uma chamada para a API está em curso.
# A label `_talk_to` (em script.rpy) controla o show/hide; esta screen
# apenas desenha um balão "..." animado e (opcionalmente) o tempo decorrido.

screen api_thinking(speaker=None, handle=None):
    zorder 100
    # Não bloqueia cliques na UI principal (é apenas decorativo).
    modal False

    # Caixa pequena no rodapé central, acima da textbox de diálogo padrão.
    frame:
        xalign 0.5
        yalign 0.92
        background "#000000a0"
        padding (24, 12)

        hbox:
            spacing 12

            text "[speaker!q] está pensando" if speaker else "Pensando":
                color "#ffffff"
                size 22

            # Animação dos pontinhos: 1, 2, 3, 1, 2, 3, ...
            text "...":
                color "#ffffff"
                size 22
                at thinking_dots

            if handle is not None:
                text "([handle.elapsed_ms()] ms)":
                    color "#aaaaaa"
                    size 16


# Animação simples dos três pontos: troca opacidade em loop.
transform thinking_dots:
    alpha 0.2
    linear 0.4 alpha 1.0
    linear 0.4 alpha 0.2
    repeat
