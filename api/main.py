"""API FastAPI da solução (ARCHITECTURE.md, seção 10). Documentação OpenAPI em /docs.

Lê dim_local, features, scores e indicadores_ano do Postgres e os modelos @champion do MLflow.
O modelo é carregado na subida e, no máximo a cada INTERVALO_S, as rotas que o usam reconferem o
@champion no registry e recarregam se a versão mudou. Se ainda não houver campeão registrado, a API
sobe mesmo assim, /health mostra o motivo e essas rotas respondem 503 até ele existir.
"""
import os
import time
from contextlib import asynccontextmanager

import pandas as pd
import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from src.modelagem import scoring

MLFLOW = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
FEATURES_PRINCIPAIS = ["acidentes_4t", "acidentes_vitima_4t", "rel_acidentes_vitima_4t", "acidentes_fatal_4t",
                       "trimestres_desde_acidente_vitima", "trimestres_consecutivos_com_acidente",
                       "acidentes_bairro_1t", "velocidade_max_via", "media_pedestre", "media_moto"]
INTERVALO_S = 60  # no máximo uma consulta ao registry por minuto, mesmo com o MLflow fora
# carregado = (campeoes, modelos), trocado de uma vez: nenhuma rota vê a versão de um e o modelo de outro.
estado: dict = {"carregado": None, "erro": "modelo ainda não carregado", "conferido_em": float("-inf")}


# ---------- acesso a dados (os testes substituem estas funções) ----------

def consultar(sql: str, **params) -> pd.DataFrame:
    from src.comum.db import engine

    return pd.read_sql(text(sql), engine(), params=params)


def banco_ok() -> bool:
    try:
        consultar("SELECT 1 AS ok")
        return True
    except Exception:
        return False


def mlflow_ok() -> bool:
    try:
        return requests.get(f"{MLFLOW}/health", timeout=3).ok
    except requests.RequestException:
        return False


def _versoes(campeoes: dict) -> dict:
    return {alvo: info["versao"] for alvo, info in campeoes.items()}


def carregar_modelo() -> bool:
    """Confere o @champion no registry e carrega os modelos se a versão mudou; devolve se há modelo."""
    estado["conferido_em"] = time.monotonic()  # antes da consulta: pedidos simultâneos não repetem a tentativa
    try:
        campeoes = scoring.modelos_campeoes()
        if estado["carregado"] is None or _versoes(estado["carregado"][0]) != _versoes(campeoes):
            estado["carregado"] = (campeoes, scoring.carregar_modelos(campeoes))
        estado["erro"] = None
    except Exception as erro:  # sem campeão ou MLflow fora: a API segue de pé, com o modelo que já tinha
        estado["erro"] = f"{type(erro).__name__}: {erro}"
    return estado["carregado"] is not None


def _exigir_modelo() -> tuple[dict, dict]:
    """(campeoes, modelos) em uso; reconfere o registry se já passou INTERVALO_S da última vez."""
    if time.monotonic() - estado["conferido_em"] >= INTERVALO_S:
        carregar_modelo()
    carregado = estado["carregado"]
    if carregado is None:
        raise HTTPException(503, f"nenhum modelo @champion disponível ({estado['erro']}); rode a dag_treino")
    return carregado


def _scores() -> pd.DataFrame:
    try:
        return consultar("SELECT s.*, d.bairro, d.logradouro FROM scores s JOIN dim_local d USING (local_id) "
                         "ORDER BY s.score_vitima DESC")
    except Exception as erro:
        raise HTTPException(503, "tabela scores indisponível; rode a dag_scoring") from erro


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    carregar_modelo()
    yield


app = FastAPI(title="Risco viário no Recife",
              description="Ranking de locais por risco de acidente com vítima no próximo trimestre (CTTU).",
              version="1.0.0", lifespan=ciclo_de_vida)


# ---------- esquemas ----------

class Saude(BaseModel):
    api: str
    banco: str
    mlflow: str
    modelo: str
    detalhe_modelo: str | None = None


class Local(BaseModel):
    posicao: int
    local_id: str
    bairro: str | None
    logradouro: str | None
    score_vitima: float
    score_atropelamento: float | None = None
    risco_alto: bool
    trimestre_base: str
    trimestre_alvo: str


class Historico(BaseModel):
    trimestre: str
    acidentes: int
    acidentes_vitima: int


class DetalheLocal(BaseModel):
    local_id: str
    bairro: str | None
    logradouro: str | None
    n_acidentes_serie: int
    score: Local | None
    historico: list[Historico]
    features_principais: dict[str, float | None]


class PedidoScore(BaseModel):
    local_id: str
    trimestre: str | None = None  # padrão: o trimestre mais recente das features


class RespostaScore(BaseModel):
    local_id: str
    trimestre_base: str
    trimestre_alvo: str
    score_vitima: float
    score_atropelamento: float | None = None
    risco_alto: bool
    versao_modelo: str


class ModeloInfo(BaseModel):
    alvo: str
    nome: str
    versao: str
    run_id: str
    modelo: str | None
    limiar: float
    treinado_em: str


class Metricas(BaseModel):
    alvo: str
    nome: str
    versao: str
    run_id: str
    metricas: dict[str, float]


class Indicador(BaseModel):
    ano: int
    acidentes: int
    acidentes_com_vitima: int
    vitimas: int
    vitimas_fatais: int
    atropelamentos_com_vitima: int
    com_pedestre: int
    com_ciclista: int
    com_moto: int


def _texto(v) -> str | None:
    return None if v is None or pd.isna(v) else str(v)


def _local(posicao: int, linha: pd.Series) -> Local:
    return Local(posicao=posicao, local_id=linha["local_id"], bairro=_texto(linha.get("bairro")),
                 logradouro=_texto(linha.get("logradouro")), score_vitima=float(linha["score_vitima"]),
                 score_atropelamento=None if pd.isna(linha.get("score_atropelamento")) else float(linha["score_atropelamento"]),
                 risco_alto=bool(linha["risco_alto"]), trimestre_base=linha["trimestre_base"],
                 trimestre_alvo=linha["trimestre_alvo"])


# ---------- rotas ----------

@app.get("/health", response_model=Saude)
def health() -> Saude:
    """Status da API, do banco e do MLflow (e se há modelo carregado)."""
    tem_modelo = estado["carregado"] is not None
    return Saude(api="ok", banco="ok" if banco_ok() else "fora", mlflow="ok" if mlflow_ok() else "fora",
                 modelo="carregado" if tem_modelo else "ausente", detalhe_modelo=None if tem_modelo else estado["erro"])


@app.get("/locais", response_model=list[Local])
def locais(bairro: str | None = Query(None, description="filtra pelo bairro (sem diferenciar maiúsculas)"),
           limit: int = Query(50, ge=1, le=2000)) -> list[Local]:
    """Ranking dos locais por score de risco (maior primeiro)."""
    scores = _scores().reset_index(drop=True)
    scores["posicao"] = scores.index + 1  # posição no ranking da cidade, mesmo com filtro
    if bairro:
        scores = scores[scores["bairro"].fillna("").str.upper() == bairro.strip().upper()]
    return [_local(int(linha["posicao"]), linha) for _, linha in scores.head(limit).iterrows()]


@app.get("/locais/{local_id}", response_model=DetalheLocal)
def detalhe_local(local_id: str) -> DetalheLocal:
    """Rótulo, histórico por trimestre, score atual e as features principais do local."""
    dim = consultar("SELECT * FROM dim_local WHERE local_id = :id", id=local_id)
    if dim.empty:
        raise HTTPException(404, f"local_id {local_id} não existe em dim_local")
    feats = consultar("SELECT * FROM features WHERE local_id = :id ORDER BY trimestre", id=local_id)
    try:
        scores = _scores().reset_index(drop=True)
    except HTTPException:  # antes da primeira dag_scoring: o detalhe sai sem score
        scores = pd.DataFrame(columns=["local_id"])
    no_ranking = scores.index[scores["local_id"] == local_id]
    score = _local(int(no_ranking[0]) + 1, scores.loc[no_ranking[0]]) if len(no_ranking) else None
    historico = [Historico(trimestre=r["trimestre"], acidentes=int(r["acidentes_1t"]),
                           acidentes_vitima=int(r["acidentes_vitima_1t"])) for _, r in feats.tail(8).iterrows()]
    ultima = feats.iloc[-1] if len(feats) else pd.Series(dtype=object)
    principais = {c: None if pd.isna(ultima.get(c)) else float(ultima[c]) for c in FEATURES_PRINCIPAIS}
    d = dim.iloc[0]
    return DetalheLocal(local_id=local_id, bairro=_texto(d["bairro"]), logradouro=_texto(d["logradouro"]),
                        n_acidentes_serie=int(d["n_acidentes"]), score=score, historico=historico,
                        features_principais=principais)


@app.post("/score", response_model=RespostaScore)
def score(pedido: PedidoScore) -> RespostaScore:
    """Inferência sob demanda: pontua um local com as features de um trimestre."""
    campeoes, modelos = _exigir_modelo()
    if pedido.trimestre:
        linhas = consultar("SELECT * FROM features WHERE local_id = :id AND trimestre = :t",
                           id=pedido.local_id, t=pedido.trimestre)
    else:
        linhas = consultar("SELECT * FROM features WHERE local_id = :id ORDER BY trimestre DESC LIMIT 1",
                           id=pedido.local_id)
    if linhas.empty:
        raise HTTPException(404, "não há features para esse local (e trimestre); ele está na grade?")
    r = scoring.pontuar(linhas, modelos, campeoes).iloc[0]
    return RespostaScore(local_id=r["local_id"], trimestre_base=r["trimestre_base"], trimestre_alvo=r["trimestre_alvo"],
                         score_vitima=float(r["score_vitima"]),
                         score_atropelamento=float(r["score_atropelamento"]) if "score_atropelamento" in r else None,
                         risco_alto=bool(r["risco_alto"]), versao_modelo=str(r["versao_modelo"]))


@app.get("/metrics", response_model=list[Metricas])
def metricas() -> list[Metricas]:
    """Métricas dos modelos em produção (teste 2024 e validação 2023), lidas do MLflow."""
    from mlflow.tracking import MlflowClient

    campeoes, _ = _exigir_modelo()
    cliente = MlflowClient()
    return [Metricas(alvo=alvo, nome=c["nome"], versao=str(c["versao"]), run_id=c["run_id"],
                     metricas=cliente.get_run(c["run_id"]).data.metrics)
            for alvo, c in campeoes.items()]


@app.get("/modelo", response_model=list[ModeloInfo])
def modelo() -> list[ModeloInfo]:
    """Versão, run_id e data de treino dos modelos carregados (um por alvo)."""
    campeoes, _ = _exigir_modelo()
    return [ModeloInfo(alvo=alvo, nome=c["nome"], versao=str(c["versao"]), run_id=c["run_id"], modelo=c["modelo"],
                       limiar=c["limiar"], treinado_em=c["treinado_em"]) for alvo, c in campeoes.items()]


@app.get("/indicadores", response_model=list[Indicador])
def indicadores() -> list[Indicador]:
    """Indicadores do Projeto 6 por ano (aba 1 do dashboard): volume, vítimas, atropelamentos e
    usuários vulneráveis. Rota a mais em relação à seção 10 (ARCHITECTURE.md, seção 17.6)."""
    try:
        tabela = consultar("SELECT * FROM indicadores_ano ORDER BY ano")
    except Exception as erro:
        raise HTTPException(503, "tabela indicadores_ano indisponível; rode a dag_ingestao_preparo") from erro
    return [Indicador(**{k: int(v) for k, v in linha.items()}) for linha in tabela.to_dict("records")]
