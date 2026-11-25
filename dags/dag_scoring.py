"""Scoring semanal e logo depois de cada treino (ARCHITECTURE.md, seções 8.2 e 9).

carregar_modelo -> gerar_inferencias -> gravar_scores -> publicar_aviso (MQTT
viario/modelo/versao). Pontua o trimestre mais recente da tabela features com os modelos
@champion dos dois alvos. Roda toda semana e também quando a dag_treino registra um campeão novo
(asset "modelo_campeao"), então numa subida do zero o primeiro scoring vem logo depois do treino.
"""
import pendulum
from airflow.sdk import Asset, AssetOrTimeSchedule, dag, task
from airflow.timetables.trigger import CronTriggerTimetable

MODELO = Asset("modelo_campeao")  # emitido pela tarefa registrar_campeao da dag_treino


@dag(dag_id="dag_scoring",
     schedule=AssetOrTimeSchedule(timetable=CronTriggerTimetable("@weekly", timezone="UTC"), assets=[MODELO]),
     start_date=pendulum.datetime(2026, 1, 1, tz="UTC"), catchup=False, tags=["am"])
def dag_scoring():
    @task
    def carregar_modelo() -> dict:
        from airflow.sdk.exceptions import AirflowFailException
        from mlflow.exceptions import MlflowException

        from src.modelagem.scoring import modelos_campeoes

        try:
            return modelos_campeoes()
        except MlflowException as erro:
            # Sem campeão registrado não adianta tentar de novo: falha já, dizendo o que fazer.
            if erro.error_code not in ("RESOURCE_DOES_NOT_EXIST", "INVALID_PARAMETER_VALUE"):
                raise
            raise AirflowFailException(
                "Ainda não há modelo @champion no MLflow, então não há o que pontuar. A dag_treino registra o "
                "campeão e, ao terminar, dispara esta DAG sozinha; numa subida do zero, espere a "
                f"dag_ingestao_preparo e a dag_treino terminarem. Detalhe do MLflow: {erro.message}") from erro

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
