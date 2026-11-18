"""Treino mensal, também disparável à mão (ARCHITECTURE.md, seções 7 e 9).

carregar_features -> split_temporal -> treinar_baseline -> comparar_modelos -> otimizar ->
registrar_campeao. Cada tarefa roda os dois alvos e grava o estado em
data/processed/modelagem/, de onde a tarefa seguinte lê.
"""
import pendulum
from airflow.sdk import dag, task


@dag(dag_id="dag_treino", schedule="@monthly", start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
     catchup=False, tags=["am"])
def dag_treino():
    @task
    def carregar_features() -> int:
        from src.modelagem.treino import carregar_features as carregar

        n = len(carregar())
        assert n, "tabela features vazia: rode a dag_ingestao_preparo antes"
        return n

    @task
    def split_temporal() -> dict:
        from src.modelagem.treino import carregar_features as carregar
        from src.modelagem.validacao import split_temporal as dividir
        from src.preparo.features import ALVOS

        features = carregar()
        return {alvo: {parte: len(linhas) for parte, linhas in dividir(features, alvo).items()} for alvo in ALVOS}

    @task
    def treinar_baseline() -> None:
        from src.modelagem.treino import treinar_baseline as treinar

        treinar()

    @task
    def comparar_modelos() -> dict:
        from src.modelagem.treino import comparar_modelos as comparar

        return comparar()

    @task
    def otimizar() -> dict:
        from src.modelagem.treino import otimizar as otimizar_

        return otimizar_()

    @task
    def registrar_campeao() -> dict:
        from src.modelagem.treino import registrar_campeao as registrar

        return {alvo: {k: r[k] for k in ("nome", "versao", "run_id", "modelo")} for alvo, r in registrar().items()}

    carregar_features() >> split_temporal() >> treinar_baseline() >> comparar_modelos() >> otimizar() >> registrar_campeao()


dag_treino()
