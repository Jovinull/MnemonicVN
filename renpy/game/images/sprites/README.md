# Sprites modulares

Os personagens são montados em runtime via `layeredimage` (ver `characters.rpy`).
Cada NPC tem três camadas independentes — assim a mesma roupa pode ser reutilizada
com vários humores, e novos NPCs reaproveitam corpos.

```
sprites/
  bodies/    # corpo base (sem cabeça/roupa). Ex.: aria_body.png
  heads/     # cabeças por humor.            Ex.: aria_head_feliz.png
  outfits/   # roupas.                       Ex.: aria_outfit_casual.png
```

O sprite final é referenciado como `aria` (variante padrão) ou
`aria feliz formal`, e o objeto `aria_dynamic` reage automaticamente à
variável `aria_humor` que é atualizada pela API após cada `/interact`.
