"""Scoring semanal (ARCHITECTURE.md, seções 8.2 e 9).

carregar_modelo -> gerar_inferencias -> gravar_scores -> publicar_aviso (MQTT
viario/modelo/versao). Pontua o trimestre mais recente da tabela features com os modelos
@champion dos dois alvos.
"""
import pendulum
from airflow.sdk import dag, task


@dag(dag_id="dag_scoring", schedule="@weekly", start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
     catchup=False, tags=["am"])
def dag_scoring():
    @task
    def carregar_modelo() -> dict:
        from src.modelagem.scoring import modelos_campeoes

        return modelos_campeoes()

    @task
    def gerar_inferencias(campeoes: dict) -> str:
        from src.modelagem.scoring import gerar_inferencias as gerar

        return str(gerar(campeoes))

    @task
    def gravar_scores(caminho: str) -> int:
        from src.modelagem.scoring import gravar_scores as gravar

        return gravar(caminho)

    @task
    def publicar_aviso(campeoes: dict, n_locais: int) -> None:
        from src.modelagem.scoring import publicar_aviso as publicar

        publicar(campeoes, n_locais)

    campeoes = carregar_modelo()
    n_locais = gravar_scores(gerar_inferencias(campeoes))
    publicar_aviso(campeoes, n_locais)


dag_scoring()
