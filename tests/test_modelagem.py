"""Tests for src/modelagem: the pipeline is fitted on the training rows only, and the metrics."""
import numpy as np
import pandas as pd
import pytest

from src.modelagem import metricas
from src.modelagem.pipeline import colunas_do_modelo, matriz, montar_pipeline


def _features(n: int = 400, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tri = np.where(np.arange(n) < n // 2, "2021Q1", "2023Q1")
    futuro = tri == "2023Q1"
    return pd.DataFrame({
        "local_id": [f"l{i % 50}" for i in range(n)],
        "trimestre": tri,
        # No "futuro" os valores mudam de patamar: se o pipeline olhasse essas linhas, a mediana mudaria.
        "acidentes_4t": np.where(futuro, 100.0, rng.integers(0, 5, n)),
        "velocidade_max_via": np.where(rng.random(n) < .3, np.nan, np.where(futuro, 80.0, 40.0)),
        "sinalizacao": np.where(futuro, "NOVA", rng.choice(["PERFEITO ESTADO", "INCOMPLETA"], n)),
        "bairro": np.where(futuro, "BAIRRO FUTURO", [f"B{i % 30}" for i in range(n)]),
        "y_vitima": rng.integers(0, 2, n),
        "y_atropelamento": rng.integers(0, 2, n),
    })


def test_pipeline_ajusta_so_no_treino():
    feats = _features()
    treino = feats[feats["trimestre"] == "2021Q1"]
    pipe = montar_pipeline(feats, "regressao_logistica").fit(matriz(treino), treino["y_vitima"])
    prep = pipe.named_steps["prep"]

    num = prep.named_transformers_["numericas"]
    medianas = dict(zip(["acidentes_4t", "velocidade_max_via"], num.named_steps["simpleimputer"].statistics_))
    assert medianas == {"acidentes_4t": treino["acidentes_4t"].median(),
                        "velocidade_max_via": treino["velocidade_max_via"].median()}
    assert num.named_steps["standardscaler"].mean_[0] == pytest.approx(treino["acidentes_4t"].mean())

    vistas = {c for cats in prep.named_transformers_["categoricas"].named_steps["onehotencoder"].categories_
              for c in cats} | set(prep.named_transformers_["bairro"].named_steps["onehotencoder"].categories_[0])
    assert not vistas & {"NOVA", "BAIRRO FUTURO"}
    # Bairro: no máximo 20 categorias próprias + 1 coluna "infrequente" (OUTROS) para o resto.
    assert prep.named_transformers_["bairro"].transform(matriz(feats)[["bairro"]]).shape[1] <= 21


def test_recall_e_precisao_no_topo_por_trimestre():
    y = pd.Series([1, 0, 1, 0, 1, 1, 0, 0])
    score = np.array([.9, .8, .1, .2, .7, .6, .5, .4])
    tri = pd.Series(["T1"] * 4 + ["T2"] * 4)
    # T1: top-1 acerta 1 de 2 positivos; T2: top-1 acerta 1 de 2. Recall@1 = 0,5; precisão@1 = 1.
    assert metricas.no_topo(y, score, tri, k=1) == (0.5, 1.0)
    limiar = metricas.escolher_limiar(y, score)
    assert metricas.avaliar(y, score, tri, limiar)["f1"] >= 0.5


def test_ano_pandemia_e_telemetria_fora_do_modelo():
    feats = _features().assign(ano=2021, periodo_pandemia=True, tel_passagens=1.0)
    numericas, _ = colunas_do_modelo(feats)
    assert not {"ano", "periodo_pandemia", "tel_passagens"} & set(numericas)
    assert "acidentes_4t" in numericas


def test_heuristica_ordena_por_vitimas_recentes_e_desempata_pelo_total():
    from src.modelagem.treino import score_heuristica

    parte = pd.DataFrame({"acidentes_vitima_4t": [2, 2, 5, 0], "acidentes_4t": [3, 9, 5, 40]})
    assert score_heuristica(parte).rank(ascending=False).tolist() == [3, 2, 1, 4]
