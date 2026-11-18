"""Scoring com os modelos @champion: usado pela dag_scoring e pela API (POST /score)."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

from src.modelagem.pipeline import matriz
from src.modelagem.treino import ALIAS, NOME_REGISTRO, ROOT, carregar_features

SCORES = ROOT / "data" / "processed" / "scores.parquet"
ALVO_PRIMARIO = "y_vitima"


def modelos_campeoes() -> dict:
    """Nome, versão, run_id, limiar e data de treino do @champion de cada alvo."""
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    c, campeoes = MlflowClient(), {}
    for alvo, nome in NOME_REGISTRO.items():
        versao = c.get_model_version_by_alias(nome, ALIAS)
        run = c.get_run(versao.run_id)
        campeoes[alvo] = {
            "nome": nome, "versao": versao.version, "run_id": versao.run_id,
            "modelo": run.data.params.get("modelo"), "limiar": run.data.metrics["val_limiar"],
            "treinado_em": datetime.fromtimestamp(run.info.start_time / 1000, timezone.utc).isoformat(timespec="seconds"),
        }
    return campeoes


def carregar_modelos(campeoes: dict) -> dict:
    return {alvo: mlflow.sklearn.load_model(f"models:/{info['nome']}@{ALIAS}") for alvo, info in campeoes.items()}


def pontuar(linhas: pd.DataFrame, modelos: dict, campeoes: dict) -> pd.DataFrame:
    """Score de cada alvo por linha de features, e risco_alto pelo limiar do alvo primário
    (o limiar que maximizou o F1 na validação, registrado no run do campeão)."""
    linhas = linhas.reset_index(drop=True)
    X = matriz(linhas)
    saida = pd.DataFrame({
        "local_id": linhas["local_id"],
        "trimestre_base": linhas["trimestre"],
        "trimestre_alvo": [str(pd.Period(t, freq="Q") + 1) for t in linhas["trimestre"]],
    })
    for alvo, modelo in modelos.items():
        saida[f"score_{alvo.removeprefix('y_')}"] = modelo.predict_proba(X)[:, 1]
    primario = campeoes[ALVO_PRIMARIO]
    saida["risco_alto"] = saida["score_vitima"] >= primario["limiar"]
    saida["versao_modelo"] = str(primario["versao"])
    saida["run_id"] = primario["run_id"]
    saida["gerado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return saida.sort_values("score_vitima", ascending=False, ignore_index=True)


def gerar_inferencias(campeoes: dict) -> Path:
    """Pontua o trimestre mais recente das features: o alvo dele é o trimestre seguinte."""
    features = carregar_features()
    recentes = features[features["trimestre"] == features["trimestre"].max()]
    pontuar(recentes, carregar_modelos(campeoes), campeoes).to_parquet(SCORES, index=False)
    return SCORES


def gravar_scores(caminho: str | Path) -> int:
    from src.comum.db import engine

    scores = pd.read_parquet(caminho)
    scores.to_sql("scores", engine(), if_exists="replace", index=False)
    return len(scores)


def publicar_aviso(campeoes: dict, n_locais: int) -> None:
    """viario/modelo/versao, retido, para o dashboard saber que há scores novos."""
    from src.comum import mqtt

    c = mqtt.cliente("dag_scoring")
    c.connect(mqtt.HOST, mqtt.PORTA)
    c.loop_start()
    primario = campeoes[ALVO_PRIMARIO]
    aviso = {"versao": str(primario["versao"]), "run_id": primario["run_id"], "gerado_em": mqtt.agora(),
             "n_locais": n_locais}
    c.publish("viario/modelo/versao", json.dumps(aviso), qos=1, retain=True).wait_for_publish(10)
    c.loop_stop()
    c.disconnect()
