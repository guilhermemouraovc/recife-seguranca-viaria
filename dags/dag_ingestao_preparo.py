"""Ingestão e preparo, mensal (ARCHITECTURE.md, seção 9).

baixar_csvs -> normalizar_schema -> limpar -> construir_local_id -> montar_features -> validar.
Cada tarefa chama a função do src/ que também roda pela linha de comando. Os imports ficam
dentro das tarefas para o dag-processor não carregar pandas a cada leitura do arquivo.
"""
import subprocess
import sys

import pendulum
from airflow.sdk import dag, task


@dag(dag_id="dag_ingestao_preparo", schedule="@monthly", start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
     catchup=False, tags=["am"])
def dag_ingestao_preparo():
    @task
    def baixar_csvs() -> int:
        from src.ingestao.fetch_datasets import SLUG, fetch_dataset

        return len(fetch_dataset(SLUG, org_dir="cttu"))  # 0 quando nada mudou no portal

    @task
    def normalizar_schema() -> int:
        from src.preparo.clean_sinistros import etapa_normalizar_schema

        return len(etapa_normalizar_schema())

    @task
    def limpar() -> int:
        from src.preparo.clean_sinistros import etapa_limpar

        return etapa_limpar()

    @task
    def construir_local_id() -> int:
        from src.preparo.local_id import executar

        return executar()["locais_distintos"]

    @task
    def montar_features() -> int:
        from src.preparo.features import executar

        return len(executar())

    @task
    def validar() -> None:
        """Asserts de dados e o teste de não-vazamento; um teste que falha derruba a DAG."""
        testes = ["tests/test_dados.py", "tests/test_features.py", "tests/test_validacao.py"]
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *testes], cwd="/app")
        if r.returncode:
            raise RuntimeError(f"validação falhou (pytest saiu com {r.returncode})")

    baixar_csvs() >> normalizar_schema() >> limpar() >> construir_local_id() >> montar_features() >> validar()


dag_ingestao_preparo()
