# characters.rpy
# Sistema modular de personagens. Cada NPC é montado em runtime via
# `layeredimage` com 4 camadas independentes, na ordem de empilhamento:
#
#   1. body    — corpo nu (sempre visível)
#   2. outfit  — roupa
#   3. hair    — cabelo (vai por cima da roupa para mostrar mechas no ombro)
#   4. expression — sobreposição da expressão facial (boca/olhos)
#
# A variável `<personagem>_humor` (ex.: `aria_humor`) é atualizada pela API
# após cada `/interact`. O `ConditionSwitch` correspondente troca a expressão
# automaticamente sem precisar de `show` manual a cada turno.

# ============================================================
# Variáveis de estado (default — persistem em saves do Ren'Py)
# ============================================================
default aria_humor = "neutro"
default aria_outfit = "seifuku"

default mei_humor = "neutro"
default mei_outfit = "casual"

default sayuri_humor = "neutro"
default sayuri_outfit = "office"


# ============================================================
# Definições de Character (lado de diálogo)
# ============================================================
define aria   = Character("Aria",   color="#f4c542")  # loira, dourado
define mei    = Character("Mei",    color="#f29ad6")  # rosa
define sayuri = Character("Sayuri", color="#9b87c8")  # lilás (madura)


# ============================================================
# ARIA — estudante, corpo inteiro (Female asset)
# ============================================================
layeredimage aria_full:
    always:
        "sprites/bodies/aria_body.png"

    group outfit:
        attribute seifuku default:
            "sprites/outfits/aria_outfit_seifuku.png"
        attribute casual:
            "sprites/outfits/aria_outfit_casual.png"
        attribute pajama:
            "sprites/outfits/aria_outfit_pajama.png"

    always:
        "sprites/hair/aria_hair.png"

    group expression:
        attribute neutro default:
            "sprites/heads/aria_head_neutro.png"
        attribute feliz:
            "sprites/heads/aria_head_feliz.png"
        attribute triste:
            "sprites/heads/aria_head_triste.png"
        attribute irritado:
            "sprites/heads/aria_head_irritado.png"


# Sprite reativo: segue automaticamente as variáveis aria_humor / aria_outfit.
image aria_dynamic = ConditionSwitch(
    "aria_humor == 'feliz' and aria_outfit == 'casual'",      "aria_full feliz casual",
    "aria_humor == 'feliz' and aria_outfit == 'pajama'",      "aria_full feliz pajama",
    "aria_humor == 'feliz'",                                  "aria_full feliz seifuku",
    "aria_humor == 'triste' and aria_outfit == 'casual'",     "aria_full triste casual",
    "aria_humor == 'triste' and aria_outfit == 'pajama'",     "aria_full triste pajama",
    "aria_humor == 'triste'",                                 "aria_full triste seifuku",
    "aria_humor == 'irritado' and aria_outfit == 'casual'",   "aria_full irritado casual",
    "aria_humor == 'irritado' and aria_outfit == 'pajama'",   "aria_full irritado pajama",
    "aria_humor == 'irritado'",                               "aria_full irritado seifuku",
    "aria_outfit == 'casual'",                                "aria_full neutro casual",
    "aria_outfit == 'pajama'",                                "aria_full neutro pajama",
    "True",                                                   "aria_full neutro seifuku",
)


# ============================================================
# MEI — meio-corpo / closeup (Halfbody Female asset)
# ============================================================
layeredimage mei_full:
    always:
        "sprites/bodies/mei_body.png"

    group outfit:
        attribute casual default:
            "sprites/outfits/mei_outfit_casual.png"
        attribute seifuku:
            "sprites/outfits/mei_outfit_seifuku.png"
        attribute pajama:
            "sprites/outfits/mei_outfit_pajama.png"

    always:
        "sprites/hair/mei_hair.png"

    group expression:
        attribute neutro default:
            "sprites/heads/mei_head_neutro.png"
        attribute feliz:
            "sprites/heads/mei_head_feliz.png"
        attribute triste:
            "sprites/heads/mei_head_triste.png"
        attribute irritado:
            "sprites/heads/mei_head_irritado.png"


image mei_dynamic = ConditionSwitch(
    "mei_humor == 'feliz' and mei_outfit == 'seifuku'",       "mei_full feliz seifuku",
    "mei_humor == 'feliz' and mei_outfit == 'pajama'",        "mei_full feliz pajama",
    "mei_humor == 'feliz'",                                   "mei_full feliz casual",
    "mei_humor == 'triste' and mei_outfit == 'seifuku'",      "mei_full triste seifuku",
    "mei_humor == 'triste' and mei_outfit == 'pajama'",       "mei_full triste pajama",
    "mei_humor == 'triste'",                                  "mei_full triste casual",
    "mei_humor == 'irritado' and mei_outfit == 'seifuku'",    "mei_full irritado seifuku",
    "mei_humor == 'irritado' and mei_outfit == 'pajama'",     "mei_full irritado pajama",
    "mei_humor == 'irritado'",                                "mei_full irritado casual",
    "mei_outfit == 'seifuku'",                                "mei_full neutro seifuku",
    "mei_outfit == 'pajama'",                                 "mei_full neutro pajama",
    "True",                                                   "mei_full neutro casual",
)


# ============================================================
# SAYURI — mulher madura (Mature Woman asset)
# ============================================================
layeredimage sayuri_full:
    always:
        "sprites/bodies/sayuri_body.png"

    group outfit:
        attribute office default:
            "sprites/outfits/sayuri_outfit_office.png"
        attribute casual:
            "sprites/outfits/sayuri_outfit_casual.png"
        attribute dress:
            "sprites/outfits/sayuri_outfit_dress.png"

    always:
        "sprites/hair/sayuri_hair.png"

    group expression:
        attribute neutro default:
            "sprites/heads/sayuri_head_neutro.png"
        attribute feliz:
            "sprites/heads/sayuri_head_feliz.png"
        attribute triste:
            "sprites/heads/sayuri_head_triste.png"
        attribute irritado:
            "sprites/heads/sayuri_head_irritado.png"


image sayuri_dynamic = ConditionSwitch(
    "sayuri_humor == 'feliz' and sayuri_outfit == 'casual'",    "sayuri_full feliz casual",
    "sayuri_humor == 'feliz' and sayuri_outfit == 'dress'",     "sayuri_full feliz dress",
    "sayuri_humor == 'feliz'",                                  "sayuri_full feliz office",
    "sayuri_humor == 'triste' and sayuri_outfit == 'casual'",   "sayuri_full triste casual",
    "sayuri_humor == 'triste' and sayuri_outfit == 'dress'",    "sayuri_full triste dress",
    "sayuri_humor == 'triste'",                                 "sayuri_full triste office",
    "sayuri_humor == 'irritado' and sayuri_outfit == 'casual'", "sayuri_full irritado casual",
    "sayuri_humor == 'irritado' and sayuri_outfit == 'dress'",  "sayuri_full irritado dress",
    "sayuri_humor == 'irritado'",                               "sayuri_full irritado office",
    "sayuri_outfit == 'casual'",                                "sayuri_full neutro casual",
    "sayuri_outfit == 'dress'",                                 "sayuri_full neutro dress",
    "True",                                                     "sayuri_full neutro office",
)


# ============================================================
# Helper Python: aplicar humor recebido da API
# ============================================================
init python:
    HUMORES_VALIDOS = ("neutro", "feliz", "triste", "irritado")

    def apply_humor(personagem, novo_humor):
        """Atualiza a variável global `<personagem>_humor` se o valor for válido."""
        if not novo_humor:
            return
        humor = str(novo_humor).strip().lower()
        if humor not in HUMORES_VALIDOS:
            return
        if personagem == "aria":
            store.aria_humor = humor
        elif personagem == "mei":
            store.mei_humor = humor
        elif personagem == "sayuri":
            store.sayuri_humor = humor
