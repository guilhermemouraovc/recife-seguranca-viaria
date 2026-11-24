"""Tests for api/main.py with TestClient. Banco e MLflow são substituídos por dados falsos, então
estes testes rodam sem os serviços de pé (docker compose run --rm api pytest)."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api.main as api
from src.modelagem import scoring

CAMPEOES = {
    "y_vitima": {"nome": "risco-viario", "versao": "3", "run_id": "r1", "modelo": "random_forest",
                 "limiar": 0.5, "treinado_em": "2026-11-18T10:00:00+00:00"},
    "y_atropelamento": {"nome": "risco-viario-atropelamento", "versao": "2", "run_id": "r2", "modelo": "mlp",
                        "limiar": 0.1, "treinado_em": "2026-11-18T10:00:00+00:00"},
}
DIM = pd.DataFrame({"local_id": ["aaaaaaaaaaaa", "bbbbbbbbbbbb"], "bairro": ["PINA", None],
                    "logradouro": ["AV X", "RUA Y"], "n_acidentes": [40, 3]})
SCORES = pd.DataFrame({"local_id": ["aaaaaaaaaaaa", "bbbbbbbbbbbb"], "trimestre_base": "2024Q4",
                       "trimestre_alvo": "2025Q1", "score_vitima": [0.9, 0.2], "score_atropelamento": [0.3, 0.01],
                       "risco_alto": [True, False], "versao_modelo": "3", "run_id": "r1"}).merge(DIM)
FEATURES = pd.DataFrame({"local_id": "aaaaaaaaaaaa", "trimestre": ["2024Q3", "2024Q4"],
                         "acidentes_1t": [2, 5], "acidentes_vitima_1t": [1, 4], "acidentes_4t": [9, 12]})


class ModeloFalso:
    def __init__(self, p):
        self.p = p

    def predict_proba(self, X):
        return np.column_stack([np.full(len(X), 1 - self.p), np.full(len(X), self.p)])


def _consultar(sql: str, **params) -> pd.DataFrame:
    if "FROM scores" in sql:
        return SCORES
    if "FROM dim_local" in sql:
        return DIM[DIM["local_id"] == params["id"]]
    if "FROM features" in sql:
        linhas = FEATURES[FEATURES["local_id"] == params["id"]]
        return linhas.iloc[::-1].head(1) if "LIMIT 1" in sql else linhas
    if "indicadores_ano" in sql:
        return pd.DataFrame([{"ano": 2024, "acidentes": 5000, "acidentes_com_vitima": 4400, "vitimas": 4800,
                              "vitimas_fatais": 30, "atropelamentos_com_vitima": 180, "com_pedestre": 300,
                              "com_ciclista": 150, "com_moto": 2500}])
    return pd.DataFrame({"ok": [1]})


@pytest.fixture(autouse=True)
def estado_limpo(monkeypatch):
    """Cada teste sobe a API do zero: o modelo carregado num teste não vaza para o seguinte."""
    monkeypatch.setattr(api, "estado", {**api.estado, "carregado": None, "conferido_em": float("-inf")})


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(api, "consultar", _consultar)
    monkeypatch.setattr(api, "mlflow_ok", lambda: True)
    monkeypatch.setattr(scoring, "modelos_campeoes", lambda: CAMPEOES)
    monkeypatch.setattr(scoring, "carregar_modelos", lambda c: {"y_vitima": ModeloFalso(.8), "y_atropelamento": ModeloFalso(.05)})
    monkeypatch.setattr(scoring, "matriz", lambda linhas: linhas)  # o modelo falso não olha as colunas
    with TestClient(api.app) as c:
        yield c


def test_health(cliente):
    assert cliente.get("/health").json() == {"api": "ok", "banco": "ok", "mlflow": "ok", "modelo": "carregado",
                                             "detalhe_modelo": None}


def test_ranking_e_filtro_por_bairro(cliente):
    ranking = cliente.get("/locais", params={"limit": 10}).json()
    assert [r["local_id"] for r in ranking] == ["aaaaaaaaaaaa", "bbbbbbbbbbbb"]
    assert ranking[1]["bairro"] is None  # NaN do banco vira null, não erro
    so_pina = cliente.get("/locais", params={"bairro": "pina"}).json()
    assert [(r["posicao"], r["local_id"]) for r in so_pina] == [(1, "aaaaaaaaaaaa")]


def test_detalhe_e_404(cliente):
    d = cliente.get("/locais/aaaaaaaaaaaa").json()
    assert d["score"]["posicao"] == 1 and [h["acidentes"] for h in d["historico"]] == [2, 5]
    assert d["features_principais"]["acidentes_4t"] == 12
    assert cliente.get("/locais/zzzzzzzzzzzz").status_code == 404


def test_detalhe_sem_tabela_scores(cliente, monkeypatch):
    """Antes da primeira dag_scoring o detalhe sai com score nulo, não 503."""
    def sem_scores(sql: str, **params):
        if "FROM scores" in sql:
            raise RuntimeError('relation "scores" does not exist')
        return _consultar(sql, **params)

    monkeypatch.setattr(api, "consultar", sem_scores)
    r = cliente.get("/locais/aaaaaaaaaaaa")
    assert r.status_code == 200 and r.json()["score"] is None
    assert [h["acidentes"] for h in r.json()["historico"]] == [2, 5]


def test_recarrega_o_modelo_quando_o_champion_muda(cliente, monkeypatch):
    cargas = []
    monkeypatch.setattr(scoring, "carregar_modelos", lambda c: cargas.append(c) or {"y_vitima": ModeloFalso(.2)})
    versao = lambda: {m["alvo"]: m["versao"] for m in cliente.get("/modelo").json()}["y_vitima"]
    novos = {alvo: {**c, "versao": str(int(c["versao"]) + 1)} for alvo, c in CAMPEOES.items()}
    monkeypatch.setattr(scoring, "modelos_campeoes", lambda: novos)

    assert versao() == "3" and not cargas  # dentro do intervalo: nem consulta o registry
    monkeypatch.setitem(api.estado, "conferido_em", float("-inf"))  # passou o intervalo
    assert versao() == "4" and len(cargas) == 1
    assert cliente.post("/score", json={"local_id": "aaaaaaaaaaaa"}).json()["versao_modelo"] == "4"

    monkeypatch.setitem(api.estado, "conferido_em", float("-inf"))
    assert versao() == "4" and len(cargas) == 1  # mesma versão no registry: não baixa o modelo de novo

    monkeypatch.setattr(scoring, "modelos_campeoes", lambda: (_ for _ in ()).throw(RuntimeError("mlflow fora")))
    monkeypatch.setitem(api.estado, "conferido_em", float("-inf"))
    assert versao() == "4"  # MLflow fora: segue com o modelo que já tinha


def test_carregar_modelos_usa_a_versao_lida_e_nao_o_alias(monkeypatch):
    uris = []
    monkeypatch.setattr("mlflow.sklearn.load_model", uris.append)
    scoring.carregar_modelos(CAMPEOES)
    assert uris == ["models:/risco-viario/3", "models:/risco-viario-atropelamento/2"]


def test_score_sob_demanda(cliente):
    r = cliente.post("/score", json={"local_id": "aaaaaaaaaaaa"}).json()
    assert r["trimestre_base"] == "2024Q4" and r["trimestre_alvo"] == "2025Q1"
    assert r["score_vitima"] == pytest.approx(0.8) and r["risco_alto"] is True  # 0,8 >= limiar 0,5
    assert cliente.post("/score", json={"local_id": "zzzzzzzzzzzz"}).status_code == 404


def test_modelo_e_indicadores(cliente):
    assert {m["alvo"]: m["versao"] for m in cliente.get("/modelo").json()} == {"y_vitima": "3", "y_atropelamento": "2"}
    assert cliente.get("/indicadores").json()[0]["atropelamentos_com_vitima"] == 180


def test_sem_modelo_a_api_sobe_e_responde_503(monkeypatch):
    tentativas = []

    def sem_registro():
        tentativas.append(1)
        raise RuntimeError("sem registro")

    monkeypatch.setattr(api, "consultar", _consultar)
    monkeypatch.setattr(api, "mlflow_ok", lambda: False)
    monkeypatch.setattr(scoring, "modelos_campeoes", sem_registro)
    with TestClient(api.app) as c:
        assert c.get("/health").json()["modelo"] == "ausente"
        assert c.post("/score", json={"local_id": "aaaaaaaaaaaa"}).status_code == 503
        assert c.get("/modelo").status_code == 503
    assert len(tentativas) == 1  # só a da subida: dentro do intervalo o 503 sai sem chamar o MLflow
