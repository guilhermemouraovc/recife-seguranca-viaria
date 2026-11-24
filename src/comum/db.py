"""Conexão com o Postgres da solução, a partir das variáveis POSTGRES_* do .env (via docker-compose)."""
import os
from functools import lru_cache

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


@lru_cache
def engine() -> Engine:
    # Um Engine (e um pool) por processo: criar um por chamada deixava conexões abertas até o GC.
    # URL.create escapa a senha; +psycopg2 explícito porque no SQLAlchemy 2.1 o postgresql://
    # sozinho procura o psycopg 3, que não está no requirements.
    return create_engine(URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=5432,
        database=os.environ["POSTGRES_DB"],
    ))
