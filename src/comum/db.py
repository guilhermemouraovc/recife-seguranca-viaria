"""Conexão com o Postgres da solução, a partir das variáveis POSTGRES_* do .env (via docker-compose)."""
import os

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


def engine() -> Engine:
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
