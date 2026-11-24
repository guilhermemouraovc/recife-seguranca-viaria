"""Exporta para reports/resultados/ os números do último treino oficial, para versionar no git e
citar no relatório (ARCHITECTURE.md, seções 4 a 7).

Os runs são os que `python -m src.modelagem.treino` (ou a dag_treino) gravou no estado
data/processed/modelagem/<alvo>.json; métricas e parâmetros são lidos do MLflow.
- modelos.csv: experimentos 01 e 02 (um run por modelo) e o melhor trial do Optuna no 03
- campeao.csv: o modelo @champion de cada alvo no teste de 2024, ao lado do baseline ingênuo
- campeao_<alvo>/: gráficos e tabelas do run do campeão (sem o modelo serializado)

Linha de comando: python -m src.modelagem.exportar
"""
import json

import pandas as pd
from mlflow.tracking import MlflowClient

from src.modelagem.treino import ALIAS, BASELINE, EXPERIMENTOS, HEURISTICA, NOME_REGISTRO, ROOT, _estado, _mlflow
from src.preparo.features import ALVOS

SAIDA = ROOT / "reports" / "resultados"
METRICAS = ["cv_temporal_pr_auc_mean", "cv_temporal_pr_auc_std", "cv_estratificado_pr_auc_mean",
            "val_pr_auc", "val_recall_at_50", "val_recall_at_100", "val_roc_auc", "val_prevalencia", "val_limiar"]


def conferir_mesmo_treino(alvo: str, comparacao: list[int], optuna: list[int], campeao: int) -> None:
    """Os inícios (ms) dos runs do estado têm de seguir a ordem de um treino só: comparação, Optuna, campeão."""
    if not max(comparacao) < min(optuna) <= max(optuna) < campeao:
        raise RuntimeError(f"{alvo}: o estado mistura treinos diferentes (o campeão não começou depois da comparação "
                           "e do Optuna); rode o treino completo de novo (python -m src.modelagem.treino) e exporte depois")


def exportar() -> None:
    _mlflow()
    cliente, modelos, campeoes = MlflowClient(), [], []
    estados = {alvo: _estado(alvo) for alvo in ALVOS}
    inicio = lambda r: cliente.get_run(r["run_id"]).info.start_time
    for alvo, estado in estados.items():  # confere os dois alvos antes de gravar qualquer arquivo
        assert "campeao" in estado, f"{alvo}: rode antes o treino completo (python -m src.modelagem.treino)"
        conferir_mesmo_treino(alvo, [inicio(r) for r in [*estado["comparacao"].values(), estado["heuristica"]]],
                              [inicio(r) for r in estado["otimizacao"].values()], inicio(estado["campeao"]))
    SAIDA.mkdir(parents=True, exist_ok=True)
    for alvo, estado in estados.items():
        runs =[(EXPERIMENTOS["baseline" if nome in (BASELINE, HEURISTICA) else "comparacao"], nome, r, "")
                for nome, r in {**estado["comparacao"], HEURISTICA: estado["heuristica"]}.items()]
        runs += [(EXPERIMENTOS["otimizacao"], f"{nome}_optuna", r, json.dumps(r["params"]))
                 for nome, r in estado["otimizacao"].items()]
        for experimento, nome, r, params in runs:
            metricas = cliente.get_run(r["run_id"]).data.metrics
            modelos.append({"alvo": alvo, "experimento": experimento, "modelo": nome,
                            **{m: metricas.get(m) for m in METRICAS}, "melhores_params": params, "run_id": r["run_id"]})

        campeao = estado["campeao"]
        metricas = cliente.get_run(campeao["run_id"]).data.metrics
        campeoes.append({"alvo": alvo, "modelo": campeao["modelo"],
                         "registro": f"{NOME_REGISTRO[alvo]}@{ALIAS} v{campeao['versao']}",
                         **{k: v for k, v in sorted(metricas.items())
                            if k.startswith(("test_", "heuristica_test_", "ganho_"))}, "run_id": campeao["run_id"]})
        pasta = SAIDA / f"campeao_{alvo}"
        pasta.mkdir(exist_ok=True)
        for artefato in cliente.list_artifacts(campeao["run_id"]):
            if not artefato.is_dir:  # o diretório "modelo" é o pipeline serializado: fica só no MLflow
                cliente.download_artifacts(campeao["run_id"], artefato.path, str(pasta))

    pd.DataFrame(modelos).round(4).to_csv(SAIDA / "modelos.csv", index=False)
    pd.DataFrame(campeoes).round(4).to_csv(SAIDA / "campeao.csv", index=False)
    print(f"gravado em {SAIDA}")


if __name__ == "__main__":
    exportar()
