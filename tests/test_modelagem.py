"""Tests for src/modelagem: the pipeline is fitted on the training rows only, and the metrics."""
import json

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


def test_estado_grava_por_inteiro_ou_nao_grava(tmp_path, monkeypatch):
    """O JSON só troca no os.replace: se ele falhar, o estado anterior fica intacto."""
    from src.modelagem import treino

    monkeypatch.setattr(treino, "ESTADO", tmp_path)
    treino._estado("y_vitima", top2=["knn", "mlp"])
    monkeypatch.setattr(treino.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("disco cheio")))
    with pytest.raises(OSError):
        treino._estado("y_vitima", escolhido="knn")
    assert json.loads((tmp_path / "y_vitima.json").read_text(encoding="utf-8")) == {"top2": ["knn", "mlp"]}


def test_treinar_baseline_comeca_estado_novo(tmp_path, monkeypatch):
    """Nada do treino anterior (top2, otimizacao, escolhido, campeao) sobrevive a um treino novo."""
    from src.modelagem import treino

    monkeypatch.setattr(treino, "ESTADO", tmp_path)
    for alvo in treino.ALVOS:
        treino._estado(alvo, top2=["knn", "mlp"], otimizacao={}, escolhido="knn", campeao={"versao": "3"})
    m = {"pr_auc": .3, "cv_temporal_pr_auc_mean": .2}
    falsos = {"_mlflow": lambda: None, "_dados": lambda alvo, f: (f, {"treino": f}, []), "_xy": lambda *a: (None, None),
              "montar_pipeline": lambda *a: None, "_parametros": lambda pipe: {}, "_rodar": lambda *a: ("lr", m),
              "_cv": lambda *a: {"cv_temporal_pr_auc_mean": .2}, "_heuristica": lambda *a: ("h", m),
              "_cv_estratificado": lambda *a: {"cv_estratificado_pr_auc_mean": .4}}
    for nome, falso in falsos.items():
        monkeypatch.setattr(treino, nome, falso)
    monkeypatch.setattr(treino.mlflow, "set_experiment", lambda nome: None)

    treino.treinar_baseline(pd.DataFrame())
    for alvo in treino.ALVOS:
        assert set(treino._estado(alvo)) == {"comparacao", "heuristica"}


def test_exportar_recusa_estado_de_treinos_misturados():
    from src.modelagem.exportar import conferir_mesmo_treino

    conferir_mesmo_treino("y_vitima", comparacao=[1, 2], optuna=[3, 4], campeao=5)  # um treino só: passa
    with pytest.raises(RuntimeError, match="mistura treinos"):  # comparação nova, campeão do treino anterior
        conferir_mesmo_treino("y_vitima", comparacao=[10, 11], optuna=[3, 4], campeao=5)
    with pytest.raises(RuntimeError, match="mistura treinos"):  # Optuna do treino anterior
        conferir_mesmo_treino("y_vitima", comparacao=[10, 11], optuna=[3, 4], campeao=12)


def test_exportar_leva_o_baseline_para_o_campeao_csv(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from src.modelagem import exportar

    metricas_campeao = {"test_pr_auc": .7, "val_pr_auc": .6, "heuristica_test_pr_auc": .65,
                        "baseline_test_pr_auc": .68, "baseline_test_recall_at_50": .1,
                        "ganho_test_pr_auc_sobre_baseline": .02}
    run = lambda r: SimpleNamespace(info=SimpleNamespace(start_time={"c": 1, "h": 1, "o": 2, "x": 3}[r]),
                                    data=SimpleNamespace(metrics=metricas_campeao if r == "x" else {}))
    cliente = SimpleNamespace(get_run=run, list_artifacts=lambda r: [])
    estado = {"comparacao": {"regressao_logistica": {"run_id": "c"}}, "heuristica": {"run_id": "h"},
              "otimizacao": {"knn": {"run_id": "o", "params": {}}},
              "campeao": {"run_id": "x", "modelo": "knn", "versao": "1"}}
    monkeypatch.setattr(exportar, "_mlflow", lambda: None)
    monkeypatch.setattr(exportar, "MlflowClient", lambda: cliente)
    monkeypatch.setattr(exportar, "_estado", lambda alvo: estado)
    monkeypatch.setattr(exportar, "SAIDA", tmp_path)

    exportar.exportar()
    colunas = set(pd.read_csv(tmp_path / "campeao.csv").columns)
    assert {"baseline_test_pr_auc", "baseline_test_recall_at_50", "ganho_test_pr_auc_sobre_baseline"} <= colunas
    assert "val_pr_auc" not in colunas
