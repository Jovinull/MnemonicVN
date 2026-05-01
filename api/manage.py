"""manage.py — painel de controle do backend MnemonicVN.

Uso:
    python manage.py run        # sobe o uvicorn (reload=False, igual em prod)
    python manage.py init-db    # cria o banco se não existir + extensão vector + tabelas
    python manage.py reset-db   # apaga TUDO e recria do zero, então roda o seed
    python manage.py seed       # apenas popula NPCs/Locais/Rotinas/Memórias

Use `psycopg2` direto para comandos que o SQLAlchemy não cobre bem
(CREATE DATABASE precisa de AUTOCOMMIT em uma conexão fora do banco-alvo).
Para tudo dentro do banco-alvo (extensão, schema), reusa o `engine` do
SQLAlchemy via `database.init_db`.
"""
from __future__ import annotations

import logging
import sys

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.engine.url import make_url

from config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("manage")


# ============================================================
# Helpers
# ============================================================
def _url_parts() -> dict:
    """Parseia DATABASE_URL e devolve as partes necessárias para o psycopg2."""
    url = make_url(settings.DATABASE_URL)
    return {
        "host": url.host or "localhost",
        "port": url.port or 5432,
        "user": url.username or "postgres",
        "password": url.password or "",
        "database": url.database or "vividnexus",
    }


def _connect_admin(parts: dict, dbname: str = "postgres"):
    """Conexão administrativa fora do banco-alvo, com AUTOCOMMIT.
    Necessária para CREATE/DROP DATABASE."""
    conn = psycopg2.connect(
        host=parts["host"],
        port=parts["port"],
        user=parts["user"],
        password=parts["password"],
        dbname=dbname,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def _database_exists(parts: dict) -> bool:
    conn = _connect_admin(parts)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (parts["database"],))
            return cur.fetchone() is not None
    finally:
        conn.close()


def _create_database(parts: dict) -> None:
    conn = _connect_admin(parts)
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(parts["database"])))
        logger.info("Banco '%s' criado.", parts["database"])
    finally:
        conn.close()


def _drop_database(parts: dict) -> None:
    """Encerra conexões ativas e dropa o banco."""
    conn = _connect_admin(parts)
    try:
        with conn.cursor() as cur:
            # Mata sessões abertas no banco-alvo (ignora a própria, que já está em 'postgres').
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (parts["database"],),
            )
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(parts["database"])))
        logger.info("Banco '%s' removido.", parts["database"])
    finally:
        conn.close()


# ============================================================
# Comandos
# ============================================================
def cmd_init_db() -> None:
    """Cria o banco (se necessário), instala pgvector e cria as tabelas."""
    parts = _url_parts()

    if _database_exists(parts):
        logger.info("Banco '%s' já existe — pulando CREATE DATABASE.", parts["database"])
    else:
        _create_database(parts)

    # `init_db` em database.py: CREATE EXTENSION IF NOT EXISTS vector + create_all
    from database import init_db
    init_db()
    logger.info("Schema pronto: extensão pgvector + tabelas criadas.")


def cmd_seed() -> None:
    """Popula 3 NPCs, locais, rotinas e memórias iniciais."""
    import seed
    seed.main()


def cmd_reset_db() -> None:
    """Apaga TUDO e recria do zero. Pede confirmação por padrão.

    Estratégia: drop database + recreate. Mais limpo do que `drop_all`
    porque elimina tipos órfãos (vector dimension changes, índices vetoriais,
    etc.) sem deixar rastros.
    """
    parts = _url_parts()

    confirmar = "--yes" in sys.argv or "-y" in sys.argv
    if not confirmar:
        resposta = input(
            f"Isso vai DROPAR o banco '{parts['database']}' inteiro. "
            "Tem certeza? [digite 'sim' para continuar]: "
        ).strip().lower()
        if resposta != "sim":
            logger.info("Cancelado.")
            return

    if _database_exists(parts):
        _drop_database(parts)

    cmd_init_db()
    cmd_seed()
    logger.info("Reset concluído.")


def cmd_run() -> None:
    """Sobe o uvicorn em primeiro plano. reload=False para não duplicar o
    scheduler do APScheduler (cf. comentário em main.py)."""
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
    )


COMMANDS = {
    "run":      cmd_run,
    "init-db":  cmd_init_db,
    "reset-db": cmd_reset_db,
    "seed":     cmd_seed,
}


def _print_help() -> None:
    print("Uso: python manage.py <comando>")
    print()
    print("Comandos:")
    print("  run        Sobe o servidor uvicorn (main:app, reload=False).")
    print("  init-db    Cria o banco (se preciso), instala pgvector e cria tabelas.")
    print("  reset-db   Dropa o banco inteiro, recria do zero e roda o seed.")
    print("             Aceita --yes/-y para pular a confirmação.")
    print("  seed       Popula NPCs/Locais/Rotinas/Memórias (idempotente).")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        _print_help()
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Comando desconhecido: {cmd!r}\n")
        _print_help()
        sys.exit(2)

    try:
        COMMANDS[cmd]()
    except KeyboardInterrupt:
        logger.info("Interrompido.")
        sys.exit(130)


if __name__ == "__main__":
    main()
