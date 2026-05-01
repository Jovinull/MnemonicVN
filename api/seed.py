"""seed.py — popula o banco com os 3 personagens iniciais, locais e rotinas.

Executar (com o backend já configurado e o LM Studio com o modelo de embedding
carregado, pois cada memória inicial gera um vetor):

    python seed.py

Idempotente: usa `nome` como chave natural para NPCs e Locais e só insere
o que ainda não existe.
"""
from __future__ import annotations

from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal, init_db
from memory_service import save_memory
from models import EstadoMundo, Local, NPC, Rotina


# ============================================================
# Locais — espelham os backgrounds disponíveis em renpy/source_assets/Backgrounds
# ============================================================
LOCAIS = [
    {
        "nome": "Sala de Aula",
        "descricao": "Sala 2-A do colégio. Janelas viradas para o pátio. "
                     "Cheira a giz e madeira velha. Ponto de encontro padrão "
                     "no horário escolar.",
        "coordenadas": {"x": 100, "y": 0, "z": 2},
        "background": "Classroom_Day.png",
    },
    {
        "nome": "Corredor da Escola",
        "descricao": "Corredor longo entre as salas. Armários metálicos nas "
                     "duas paredes. Barulhento entre aulas, vazio durante.",
        "coordenadas": {"x": 100, "y": 5, "z": 2},
        "background": "School_Hallway_Day.png",
    },
    {
        "nome": "Cafeteria",
        "descricao": "Cafeteria do colégio. Mesas redondas, balcão de "
                     "self-service. Cheiro de pão de melão.",
        "coordenadas": {"x": 100, "y": 10, "z": 1},
        "background": "Cafeteria_Day.png",
    },
    {
        "nome": "Quarto de Aria",
        "descricao": "Apartamento pequeno que Aria divide com a mãe. "
                     "Pôsteres de atletismo, troféus baratos, uma cama futon.",
        "coordenadas": {"x": 200, "y": 0, "z": 1},
        "background": "Bedroom_Day.png",
    },
    {
        "nome": "Quarto de Mei",
        "descricao": "Quarto silencioso, livros em pilhas verticais, um "
                     "caderno de desenho sempre fechado em cima da mesa.",
        "coordenadas": {"x": 250, "y": 0, "z": 3},
        "background": "Bedroom_Evening.png",
    },
    {
        "nome": "Apartamento de Sayuri",
        "descricao": "Living amplo, mais livros do que móveis. Janela grande "
                     "voltada para a rua. Sempre uma chaleira no fogo.",
        "coordenadas": {"x": 300, "y": 0, "z": 4},
        "background": "Sitting_Room.png",
    },
    {
        "nome": "Rua Principal",
        "descricao": "Rua comercial principal da cidade no fim de tarde. "
                     "Lanternas acendendo, cerejeiras meio carecas.",
        "coordenadas": {"x": 0, "y": 0, "z": 0},
        "background": "Street_Spring_Evening.png",
    },
    {
        "nome": "Estação de Trem",
        "descricao": "Plataforma de subúrbio ao entardecer. Vagão amarelo "
                     "esperando, anúncios distorcidos no alto-falante.",
        "coordenadas": {"x": -50, "y": 0, "z": 0},
        "background": "Train_Evening.png",
    },
    {
        "nome": "Templo",
        "descricao": "Pequeno templo no alto de uma escadaria de pedra. "
                     "Silencioso, exceto pelo vento nos sinos.",
        "coordenadas": {"x": 50, "y": 100, "z": 5},
        "background": "Temple_Spring_Afternoon.png",
    },
]


# ============================================================
# NPCs — personalidade detalhada para alimentar o system prompt do Qwen
# ============================================================
NPCS = [
    {
        "nome": "Aria Tanaka",
        "humor_atual": "neutro",
        "atributos_base": {"energia": 9, "empatia": 6, "confianca_no_jogador": 4},
        "local_inicial": "Sala de Aula",
        "personalidade": (
            "Aria Tanaka, 17 anos, estudante do 2º ano. Loira, atleta de 100m. "
            "Personalidade extrovertida, competitiva, leal a um nível imprudente. "
            "Usa humor e provocação como escudo — tem dificuldade de admitir "
            "vulnerabilidade. Detesta ser tratada como criança. Mora com a mãe "
            "num apartamento pequeno; o pai saiu há três anos sem aviso, e ela "
            "carrega isso como ressentimento e culpa misturados. Sonha com uma "
            "faculdade fora da cidade, mas se sente culpada por querer ir embora. "
            "Voz: frases curtas, exclamativas, gírias adolescentes em pt-BR "
            "('tipo', 'mano', 'deixa de ser bobo'). Quando triste fica "
            "monossilábica. Reage antes de pensar."
        ),
        "memorias_iniciais": [
            "Hoje cedo a mãe me chamou pra tomar café e eu fingi que estava "
            "dormindo. De novo. Não sei por que faço isso.",
            "Bati meu próprio recorde nos 100m semana passada. Ninguém da turma "
            "comentou nada. Tanto faz.",
            "Tem um aluno transferido novo na escola. Todo mundo tá olhando. "
            "Eu também tô olhando, mas vou fingir que não.",
        ],
    },
    {
        "nome": "Mei Kobayashi",
        "humor_atual": "neutro",
        "atributos_base": {"energia": 4, "empatia": 9, "confianca_no_jogador": 2},
        "local_inicial": "Quarto de Mei",
        "personalidade": (
            "Mei Kobayashi, 16 anos, mesmo colégio que Aria, turma diferente. "
            "Cabelo rosa pastel cobrindo metade do rosto. Introvertida, "
            "perceptiva, ansiosa. Lê literatura e mangá como distância segura "
            "do mundo. Quando confia em alguém, vira a pessoa mais leal e "
            "gentil — mas esse 'alguém' leva meses pra ser admitido. Filha "
            "única de família que se mudou três vezes em cinco anos por causa "
            "do trabalho do pai; aprendeu a não criar laços porque sempre se "
            "despede. Tem um caderno de desenhos que nunca mostrou pra "
            "ninguém. Voz: frases que começam e morrem ('ah, eu... não, "
            "esquece'). Usa 'talvez', 'acho que', 'me desculpa' em excesso. "
            "Quando feliz, sorri sem dizer nada. Quando 'irritada', é quieta, "
            "não explosiva."
        ),
        "memorias_iniciais": [
            "Desenhei o pátio da escola hoje, durante a aula de matemática. "
            "Acho que ficou bom. Não vou mostrar pra ninguém.",
            "Minha mãe perguntou se eu queria convidar alguém pra jantar. "
            "Eu disse que não tinha ninguém. Era verdade.",
            "Tem um aluno novo. Ele olhou pro meu caderno. Eu fechei rápido. "
            "Ele não insistiu. Isso foi… estranho. De um jeito bom?",
        ],
    },
    {
        "nome": "Sayuri Hoshino",
        "humor_atual": "neutro",
        "atributos_base": {"energia": 6, "empatia": 8, "confianca_no_jogador": 5},
        "local_inicial": "Sala de Aula",
        "personalidade": (
            "Sayuri Hoshino, 34 anos, professora de literatura no colégio e "
            "tutora particular nos fins de tarde. Cabelo preto preso em rabo "
            "de cavalo baixo. Calma, observadora, paciente — mas detesta "
            "injustiça, e é uma das poucas coisas que rompem sua compostura. "
            "Senso de humor seco que a maioria dos alunos não pega. Ex-"
            "pesquisadora de literatura comparada que largou a universidade "
            "depois de uma denúncia de assédio (ela foi a denunciante; o "
            "sistema não a apoiou). Voltou pra cidade natal pra ter 'menos "
            "política e mais sentido'. Mora sozinha, mais livros do que "
            "móveis. Voz: completa as frases. Usa o nome do interlocutor "
            "quando quer marcar atenção ('Veja bem, [nome]…'). Quando feliz, "
            "fala mais baixo, não mais alto. Não tenta ser legal — tenta ser "
            "justa."
        ),
        "memorias_iniciais": [
            "Recebi a lista da nova turma hoje. Reconheci dois nomes de "
            "alunos que vão precisar de paciência — e isso não é crítica, "
            "é só um dado.",
            "Comprei chá novo na lojinha perto da estação. Vou abrir hoje "
            "à noite, com o livro do Tanizaki que tô relendo.",
            "Lembrei da Universidade hoje sem querer. Fechei a janela, fiz "
            "café, voltei a corrigir provas. Funciona.",
        ],
    },
]


# ============================================================
# Rotinas — usam IDs resolvidos depois da inserção dos NPCs/Locais
# ============================================================
ROTINAS_TEMPLATE = [
    # Aria
    ("Aria Tanaka", time(7, 30),  time(8, 0),   "Estação de Trem",     "Vai pra escola correndo, chega ofegante."),
    ("Aria Tanaka", time(8, 0),   time(12, 0),  "Sala de Aula",        "Aulas matinais. Anota pouco, presta meia-atenção."),
    ("Aria Tanaka", time(12, 0),  time(13, 0),  "Cafeteria",           "Almoça em grupo, fala alto, ri."),
    ("Aria Tanaka", time(16, 0),  time(18, 0),  "Rua Principal",       "Treino de atletismo no parque, depois passa na conveniência."),
    ("Aria Tanaka", time(20, 0),  time(23, 0),  "Quarto de Aria",      "Faz dever de mau humor, escuta música alta de fone."),
    # Mei
    ("Mei Kobayashi", time(8, 30), time(12, 0), "Sala de Aula",        "Senta no canto. Desenha discretamente quando o professor vira."),
    ("Mei Kobayashi", time(12, 0), time(13, 0), "Corredor da Escola",  "Almoça sozinha, perto da janela, com um livro aberto."),
    ("Mei Kobayashi", time(15, 0), time(17, 0), "Templo",              "Vai sozinha, senta no banco de pedra, desenha."),
    ("Mei Kobayashi", time(19, 0), time(23, 0), "Quarto de Mei",       "Lê. Às vezes desenha. Quase nunca olha o celular."),
    # Sayuri
    ("Sayuri Hoshino", time(8, 0),  time(12, 0), "Sala de Aula",        "Dá aula. Calma e exigente. Chama pelo nome quem se distrai."),
    ("Sayuri Hoshino", time(13, 0), time(15, 0), "Cafeteria",           "Corrige provas com chá ao lado. Não almoça com colegas."),
    ("Sayuri Hoshino", time(16, 0), time(18, 0), "Apartamento de Sayuri","Tutoria particular pra alunos selecionados."),
    ("Sayuri Hoshino", time(20, 0), time(23, 0), "Apartamento de Sayuri","Lê. Cozinha algo simples. Fecha o dia cedo."),
]


def upsert_local(db: Session, data: dict) -> Local:
    existing = db.scalars(select(Local).where(Local.nome == data["nome"])).first()
    if existing:
        return existing
    local = Local(
        nome=data["nome"],
        descricao=data["descricao"],
        coordenadas=data["coordenadas"],
    )
    db.add(local)
    db.flush()
    return local


def upsert_npc(db: Session, data: dict, local_id: int) -> NPC:
    existing = db.scalars(select(NPC).where(NPC.nome == data["nome"])).first()
    if existing:
        return existing
    npc = NPC(
        nome=data["nome"],
        personalidade=data["personalidade"],
        atributos_base=data["atributos_base"],
        humor_atual=data["humor_atual"],
        local_atual_id=local_id,
    )
    db.add(npc)
    db.flush()
    return npc


def upsert_rotina(
    db: Session, npc_id: int, hora_inicio: time, hora_fim: time, local_id: int, acao: str
) -> Rotina:
    existing = db.scalars(
        select(Rotina)
        .where(Rotina.npc_id == npc_id)
        .where(Rotina.hora_inicio == hora_inicio)
        .where(Rotina.local_id == local_id)
    ).first()
    if existing:
        return existing
    rotina = Rotina(
        npc_id=npc_id,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        local_id=local_id,
        acao_descrita=acao,
    )
    db.add(rotina)
    db.flush()
    return rotina


def ensure_estado_mundo(db: Session) -> None:
    if db.scalars(select(EstadoMundo).limit(1)).first() is None:
        db.add(EstadoMundo(tick_atual=0, clima="ensolarado", eventos_globais_ativos=[]))


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        # Locais
        local_por_nome: dict[str, Local] = {}
        for data in LOCAIS:
            local_por_nome[data["nome"]] = upsert_local(db, data)
        db.commit()

        # NPCs
        npc_por_nome: dict[str, NPC] = {}
        for data in NPCS:
            local = local_por_nome[data["local_inicial"]]
            npc_por_nome[data["nome"]] = upsert_npc(db, data, local.id)
        db.commit()

        # Rotinas
        for nome_npc, h_ini, h_fim, nome_local, acao in ROTINAS_TEMPLATE:
            upsert_rotina(
                db,
                npc_id=npc_por_nome[nome_npc].id,
                hora_inicio=h_ini,
                hora_fim=h_fim,
                local_id=local_por_nome[nome_local].id,
                acao=acao,
            )
        db.commit()

        # Estado do mundo
        ensure_estado_mundo(db)
        db.commit()

        # Memórias iniciais (geram embeddings via Nomic — exige LM Studio rodando)
        for data in NPCS:
            npc = npc_por_nome[data["nome"]]
            for texto in data["memorias_iniciais"]:
                ja_tem = any(m.texto_original == texto for m in npc.memorias)
                if not ja_tem:
                    save_memory(db, npc_id=npc.id, texto=texto, tipo="reflexao", relevancia=0.8)

        print("Seed concluído.")
        print("NPCs criados:")
        for npc in npc_por_nome.values():
            print(f"  - id={npc.id}  {npc.nome}  (humor={npc.humor_atual})")
        print(f"Locais: {len(local_por_nome)}  |  Rotinas: {len(ROTINAS_TEMPLATE)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
