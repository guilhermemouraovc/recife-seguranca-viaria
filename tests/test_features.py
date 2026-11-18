"""Tests for src/preparo/features.py, including the no-leakage test (ARCHITECTURE.md, section 3.3)."""
import numpy as np
import pandas as pd
import pytest

from src.preparo.features import ENVOLVIDOS, MODAS, VIA_CATEGORICAS, montar_features

COLUNAS = ["local_id", "bairro_norm", "data", "hora", "com_vitima", "fatal", "endereco_cruzamento",
           "num_semaforo", "velocidade_max_via", *ENVOLVIDOS, *VIA_CATEGORICAS, *MODAS]


def _tabela(registros: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(registros).reindex(columns=COLUNAS)
    df["data"] = pd.to_datetime(df["data"])
    df["trimestre"] = df["data"].dt.to_period("Q").astype(str)
    for c in ["com_vitima", "fatal"]:
        df[c] = df[c].eq(True)
    for c in [*ENVOLVIDOS, "num_semaforo"]:
        df[c] = pd.array(df[c], dtype="Int64")
    return df


def _aleatorios(n: int = 600, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    escolha = lambda opcoes: [opcoes[i] for i in rng.integers(0, len(opcoes), n)]
    datas = pd.Timestamp("2018-01-01") + pd.to_timedelta(rng.integers(0, 3 * 365, n), unit="D")
    locais = escolha(["a", "b", "c", "d", None])
    bairros = {"a": "PINA", "b": "PINA", "c": "BOA VIAGEM", "d": "BOA VIAGEM"}
    return _tabela([{
        "local_id": locais[i], "bairro_norm": bairros.get(locais[i], "IBURA"), "data": datas[i],
        "hora": f"{rng.integers(0, 24):02d}:10:00" if rng.random() > .2 else None,
        "com_vitima": rng.random() < .4, "fatal": rng.random() < .05,
        "endereco_cruzamento": escolha(["RUA A", "R. A", "AV B", None])[i],
        "num_semaforo": escolha([12, None, None])[i], "velocidade_max_via": escolha(["60 km/h", "40KM", None])[i],
        "tempo_clima": escolha(["Bom", "Chuvoso", None])[i], "gravidade": escolha(["COM VÍTIMA", "SEM VÍTIMA"])[i],
        **{c: escolha([0, 1, 2, None])[i] for c in ENVOLVIDOS},
        **{c: escolha(["X", "y", "DESCONHECIDO", None])[i] for c in VIA_CATEGORICAS},
    } for i in range(n)])


@pytest.mark.parametrize("corte", ["2018Q2", "2019Q1", "2020Q3"])
def test_nao_vazamento(corte):
    """Features até o trimestre T não mudam quando se acrescentam acidentes depois de T."""
    acidentes, locais = _aleatorios(), ["a", "b", "c", "d"]
    assert (acidentes["trimestre"] > corte).any()
    completo = montar_features(acidentes, locais)
    so_ate_o_corte = montar_features(acidentes[acidentes["trimestre"] <= corte], locais)
    esperado = completo[completo["trimestre"] <= corte].reset_index(drop=True)
    pd.testing.assert_frame_equal(so_ate_o_corte.drop(columns="y"), esperado.drop(columns="y"), check_dtype=False)


def test_alvo_janelas_e_participacao():
    f = montar_features(_tabela([
        {"local_id": "a", "bairro_norm": "PINA", "data": "2019-02-01", "com_vitima": True},
        {"local_id": "b", "bairro_norm": "PINA", "data": "2019-05-01", "com_vitima": True},
        {"local_id": "a", "bairro_norm": "PINA", "data": "2019-08-01"},
        {"local_id": "a", "bairro_norm": "PINA", "data": "2019-08-02"},
    ]), ["a", "b"]).set_index(["local_id", "trimestre"])

    assert f.loc["a", "y"].tolist()[:2] == [0, 0] and pd.isna(f.loc[("a", "2019Q3"), "y"])
    assert f.loc[("b", "2019Q1"), "y"] == 1
    assert f.loc[("a", "2019Q3"), ["acidentes_1t", "acidentes_4t", "acidentes_vitima_4t"]].tolist() == [2, 3, 1]
    # 2019Q2 + 2019Q3 na cidade: 1 + 2 acidentes; o local b teve 1 deles.
    assert f.loc[("b", "2019Q3"), "rel_acidentes_2t"] == pytest.approx(1 / 3)
    assert f.loc["a", "trimestres_consecutivos_com_acidente"].tolist() == [1, 0, 1]
    assert f.loc["a", "trimestres_desde_acidente_vitima"].tolist() == [0, 1, 2]
    assert pd.isna(f.loc[("b", "2019Q1"), "trimestres_desde_acidente_vitima"])
    assert f.loc["a", "acidentes_bairro_1t"].tolist() == [1, 1, 2]
