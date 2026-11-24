"""Publica o que construir_local_id e montar_features gravaram em staging, depois do validar
(tarefa publicar da dag_ingestao_preparo, ARCHITECTURE.md, seção 9).

Troca as tabelas <nome>_staging pelas oficiais numa transação só e move os arquivos de
data/processed/staging/ para data/processed/. Se o validar falhar, esta etapa não roda e as
tabelas e os arquivos oficiais, que a dag_treino, a dag_scoring e a API leem, ficam como estavam.

Linha de comando (depois de local_id, features e pytest): python -m src.preparo.publicar
"""
import os

from sqlalchemy import text

from src.preparo.local_id import SAIDA, STAGING

TABELAS = ["dim_local", "indicadores_ano", "features"]


def publicar() -> list[str]:
    from src.comum.db import engine

    arquivos = sorted(STAGING.glob("*"))
    assert arquivos, f"nada para publicar em {STAGING}: rode construir_local_id e montar_features antes"
    with engine().begin() as con:  # DDL no Postgres é transacional: troca as três tabelas ou nenhuma
        for tabela in TABELAS:
            con.execute(text(f"DROP TABLE IF EXISTS {tabela}"))
            con.execute(text(f"ALTER TABLE {tabela}_staging RENAME TO {tabela}"))
    for arquivo in arquivos:
        os.replace(arquivo, SAIDA / arquivo.name)
    print(f"publicados: tabelas {', '.join(TABELAS)} e arquivos {', '.join(a.name for a in arquivos)}")
    return [a.name for a in arquivos]


if __name__ == "__main__":
    publicar()
