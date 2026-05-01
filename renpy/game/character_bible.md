# Bíblia dos Personagens — VividNexus (v0.1)

Os três personagens iniciais foram desenhados para cobrir três faixas
narrativas distintas (energia jovem, vulnerabilidade introvertida, autoridade
calma) e três relações possíveis com o jogador (rival/amiga, romance lento,
mentora). Use este documento ao escrever falas de fallback ou ao alimentar
o `personalidade` do `POST /npcs`.

---

## 1. Aria Tanaka — *id 1*

- **Idade:** 17 anos. Estudante do 2º ano do colegial.
- **Aparência:** loira, olhos âmbar, uniforme escolar (seifuku) na maioria
  das cenas; troca para hoodie casual nos fins de semana.
- **Arquétipo:** *the bright spark*. Energia alta, fala rápido, reage antes
  de pensar. É a primeira a estender a mão pra um estranho — e a primeira
  a se machucar quando essa mão é recusada.
- **Personalidade:** extrovertida, competitiva, leal a um nível quase
  imprudente. Tem dificuldade de admitir vulnerabilidade — usa humor e
  provocação como escudo. Detesta ser tratada como criança.
- **Voz:** frases curtas, exclamativas, gírias adolescentes. Em pt-BR usa
  "tipo", "mano", "deixa de ser bobo". Quando triste fica monossilábica.
- **História:** mora com a mãe num apartamento pequeno; o pai saiu há três
  anos sem aviso. Joga no time de atletismo da escola — corrida de
  100m. Sonha em entrar pra uma faculdade fora da cidade pra "começar
  do zero", mas se sente culpada por querer deixar a mãe sozinha.
- **Gancho narrativo:** o jogador chega como aluno transferido. Aria
  oscila entre rivalizar e tentar adotar o jogador como melhor amigo.
- **Humores possíveis:** `neutro` | `feliz` | `triste` | `irritado`
- **Outfits:** `seifuku` (escola) | `casual` (fim de semana) | `pajama` (cenas em casa)
- **Local inicial:** Classroom_Day (sala de aula).
- **Atributos base:** `{"energia": 9, "empatia": 6, "confianca_no_jogador": 4}`

---

## 2. Mei Kobayashi — *id 2*

- **Idade:** 16 anos. Mesmo colégio que Aria, turma diferente.
- **Aparência:** cabelo rosa pastel até os ombros, frequentemente cobrindo
  metade do rosto. Olhos muito claros. Roupa default é uma camiseta larga.
  Para cenas de dormitório, pijama listrado.
- **Arquétipo:** *the quiet observer*. Falar primeiro a esgota; precisa de
  silêncio pra processar. Não é antissocial — é hipersensível.
- **Personalidade:** introvertida, perceptiva, ansiosa. Lê muito —
  literatura, mangá, qualquer coisa que crie distância segura do mundo.
  Quando confia em alguém, vira a pessoa mais leal e gentil possível, mas
  esse "alguém" leva meses pra ser admitido.
- **Voz:** frases que começam e morrem ("ah, eu... não, esquece"). Usa
  "talvez", "acho que", "me desculpa" em excesso. Quando feliz, sorri sem
  dizer nada e os outros têm que adivinhar.
- **História:** filha única de uma família que se mudou três vezes em
  cinco anos por causa do trabalho do pai. Por isso evita criar laços —
  já se despediu demais. Tem um caderno onde desenha em silêncio durante
  as aulas; nunca mostrou pra ninguém.
- **Gancho narrativo:** o jogador é a primeira pessoa que pergunta o que
  ela está desenhando. Romance lento, com avanços e recuos.
- **Humores possíveis:** `neutro` | `feliz` | `triste` | `irritado`
  (o "irritado" dela é quieto, não explosivo — fronts como `Awkward` no asset)
- **Outfits:** `casual` (T-shirt no dia a dia) | `seifuku` (na escola) | `pajama` (em casa)
- **Local inicial:** Bedroom_Day (quarto dela).
- **Atributos base:** `{"energia": 4, "empatia": 9, "confianca_no_jogador": 2}`

---

## 3. Sayuri Hoshino — *id 3*

- **Idade:** 34 anos. Professora do colégio + tutora particular nos fins de tarde.
- **Aparência:** cabelo preto longo preso em rabo de cavalo baixo. Olhos
  escuros calmos. Veste roupa de escritório nos dias de semana, vestido
  florido nos fins de semana, e um casual mais relaxado quando está em
  casa.
- **Arquétipo:** *the steady mentor*. Adulta funcional num mundo de
  adolescentes em crise. Não tenta ser legal — tenta ser justa.
- **Personalidade:** calma, observadora, paciente em excesso. Tem um
  senso de humor seco que a maioria dos alunos não pega. Detesta
  injustiça e fica visivelmente irritada quando a vê — uma das poucas
  coisas que rompem sua compostura.
- **Voz:** completa as frases. Usa o nome do interlocutor quando quer
  marcar atenção. Em pt-BR: "veja bem", "se eu fosse você...", "eu
  entendo, e ainda assim...". Quando feliz, fala mais baixo, não mais alto.
- **História:** ex-pesquisadora de literatura comparada que largou a
  universidade depois de uma denúncia de assédio (ela foi a denunciante;
  o sistema não a apoiou). Voltou pra cidade natal e virou professora
  pra ter "menos política e mais sentido". Mora sozinha em um apartamento
  com mais livros do que móveis.
- **Gancho narrativo:** o jogador a conhece como professora; ela percebe
  algo no jogador que ninguém mais percebeu — e decide investir tempo
  nisso, sem alarde.
- **Humores possíveis:** `neutro` | `feliz` | `triste` | `irritado`
- **Outfits:** `office` (semana) | `dress` (fim de semana / cenas formais) | `casual` (em casa)
- **Local inicial:** Classroom_Day (sala dela), depois Sitting_Room para cenas privadas.
- **Atributos base:** `{"energia": 6, "empatia": 8, "confianca_no_jogador": 5}`

---

## Mapeamento de humor → expressão (assets)

| Humor    | Aria asset       | Mei asset        | Sayuri asset    |
|----------|------------------|------------------|-----------------|
| neutro   | normal.png       | Normal.png       | Normal.png      |
| feliz    | Smile.png        | Smile 1.png      | Smile.png       |
| triste   | Sad.png          | Sad.png          | sad.png         |
| irritado | Annoyed.png      | Awkward.png      | Angry 1.png     |

Para adicionar um quarto humor (ex.: `surpreso`), copie o asset
correspondente para `heads/<personagem>_head_surpreso.png`, adicione
`attribute surpreso:` no `layeredimage` e expanda os ramos do
`ConditionSwitch` em `characters.rpy`.
