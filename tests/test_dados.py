"""Data checks run by the `validar` task of dag_ingestao_preparo (ARCHITECTURE.md, section 9):
row counts, nulls in required columns, date range and targets. Skipped when the pipeline has
not produced the files yet (e.g. on a fresh clone). The DAG points DADOS_PROCESSADOS at the
staging folder, so the checks run before anything is published."""
import os
from pathlib import Path

import pandas as pd
import pytest

PROC = Path(os.environ.get("DADOS_PROCESSADOS", Path(__file__).resolve().parents[1] / "data" / "processed"))
pytestmark = pytest.mark.skipif(not (PROC / "features.parquet").exists(), reason="pipeline de preparo ainda não rodou")


def test_acidentes_linhas_nulos_e_datas():
    acidentes = pd.read_parquet(PROC / "acidentes_local.parquet")
    assert len(acidentes) > 50_000
    assert acidentes[["data", "trimestre"]].notna().all().all()
    assert acidentes["data"].min() >= pd.Timestamp("2015-01-01")
    # Sem data fixa: as linhas de dez/2025 do arquivo de 2024 saem, e o CSV de 2025, quando vier, continua passando.
    assert (acidentes["data"].dt.year == acidentes["ano_arquivo"]).all()
    assert not acidentes["situacao"].isin(["CANCELADA", "DUPLICIDADE"]).any()
    assert acidentes["local_id"].notna().mean() > 0.98


def test_features_painel_completo_e_alvos():
    f = pd.read_parquet(PROC / "features.parquet")
    assert len(f) == f["local_id"].nunique() * f["trimestre"].nunique()  # painel completo
    assert not f.duplicated(["local_id", "trimestre"]).any()
    assert f[["local_id", "trimestre", "acidentes_1t", "acidentes_4t"]].notna().all().all()
    ultimo = f["trimestre"] == f["trimestre"].max()
    for alvo in ["y_vitima", "y_atropelamento"]:
        assert f.loc[ultimo, alvo].isna().all() and f.loc[~ultimo, alvo].notna().all()
        assert set(f.loc[~ultimo, alvo].unique()) <= {0, 1}
