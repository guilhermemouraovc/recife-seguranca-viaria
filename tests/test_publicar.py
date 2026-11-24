"""Tests for src/preparo/publicar.py: the staging tables and files replace the official ones.
SQLite stands in for Postgres, so this runs without the services."""
import pandas as pd
from sqlalchemy import create_engine, inspect

from src.comum import db
from src.preparo import publicar


def test_publicar_troca_tabelas_e_move_arquivos(tmp_path, monkeypatch):
    banco = create_engine(f"sqlite:///{tmp_path / 'banco.db'}")
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(db, "engine", lambda: banco)
    monkeypatch.setattr(publicar, "STAGING", staging)
    monkeypatch.setattr(publicar, "SAIDA", tmp_path)
    for tabela in publicar.TABELAS:
        pd.DataFrame({"versao": ["oficial"]}).to_sql(tabela, banco, index=False)
        pd.DataFrame({"versao": ["staging"]}).to_sql(f"{tabela}_staging", banco, index=False)
    (tmp_path / "features.parquet").write_text("oficial")
    (staging / "features.parquet").write_text("staging")

    assert publicar.publicar() == ["features.parquet"]
    for tabela in publicar.TABELAS:
        assert pd.read_sql_table(tabela, banco)["versao"].tolist() == ["staging"]
    assert not [t for t in inspect(banco).get_table_names() if t.endswith("_staging")]
    assert (tmp_path / "features.parquet").read_text() == "staging" and not list(staging.iterdir())
