"""Treino disparado pela publicação de features novas na dag_ingestao_preparo (asset "features"),
e também à mão (ARCHITECTURE.md, seções 7 e 9).

carregar_features -> split_temporal -> treinar_baseline -> comparar_modelos -> otimizar ->
registrar_campeao. carregar_features grava um snapshot da tabela em Parquet e as demais tarefas
treinam todas sobre ele, mesmo que a tabela mude no meio. Cada tarefa roda os dois alvos e grava
o estado em data/processed/modelagem/, de onde a tarefa seguinte lê.
"""
import pendulum
from airflow.sdk import Asset, dag, task

FEATURES = Asset("features")  # emitido pela tarefa publicar da dag_ingestao_preparo


# max_active_runs=1: dois treinos ao mesmo tempo sobrescrevem o estado e o snapshot um do outro.
@dag(dag_id="dag_treino", schedule=[FEATURES], start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
     catchup=False, max_active_runs=1, tags=["am"])
def dag_treino():
    @task
    def carregar_features() -> str:
        from src.modelagem.treino import ESTADO, carregar_features as carregar

        features = carregar()
        assert len(features), "tabela features vazia: rode a dag_ingestao_preparo antes"
        ESTADO.mkdir(parents=True, exist_ok=True)
        snapshot = ESTADO / "features_treino.parquet"
        features.to_parquet(snapshot, index=False)
        return str(snapshot)

    @task
    def split_temporal(snapshot: str) -> dict:
        import pandas as pd

        from src.modelagem.validacao import split_temporal as dividir
        from src.preparo.features import ALVOS

        features = pd.read_parquet(snapshot)
        return {alvo: {parte: len(linhas) for parte, linhas in dividir(features, alvo).items()} for alvo in ALVOS}

    @task
    def treinar_baseline(snapshot: str) -> None:
        import pandas as pd

        from src.modelagem.treino import treinar_baseline as treinar

        treinar(pd.read_parquet(snapshot))

    @task
    def comparar_modelos(snapshot: str) -> dict:
        import pandas as pd

        from src.modelagem.treino import comparar_modelos as comparar

        return comparar(pd.read_parquet(snapshot))

    @task
    def otimizar(snapshot: str) -> dict:
        import pandas as pd

        from src.modelagem.treino import otimizar as otimizar_

        return otimizar_(pd.read_parquet(snapshot))

    @task
    def registrar_campeao(snapshot: str) -> dict:
        import pandas as pd

        from src.modelagem.treino import registrar_campeao as registrar

        return {alvo: {k: r[k] for k in ("nome", "versao", "run_id", "modelo")}
                for alvo, r in registrar(pd.read_parquet(snapshot)).items()}

    snapshot = carregar_features()
    (split_temporal(snapshot) >> treinar_baseline(snapshot) >> comparar_modelos(snapshot) >> otimizar(snapshot)
     >> registrar_campeao(snapshot))


dag_treino()
