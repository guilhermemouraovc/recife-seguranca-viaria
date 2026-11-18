# Airflow 3.4.0 (ARCHITECTURE.md, seção 12). As instruções até o pip install são idênticas às de
# docker/python/Dockerfile de propósito: o build reaproveita aquela camada, e as DAGs treinam com
# exatamente o mesmo scikit-learn e pandas que a api e o dashboard usam para carregar o modelo.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTEST_ADDOPTS="-p no:cacheprovider"

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Os containers rodam como AIRFLOW_UID:0 (convenção do Airflow): o grupo 0 precisa gravar no
# AIRFLOW_HOME (airflow.cfg, senhas, logs). O volume de logs herda essa permissão ao ser criado.
ENV AIRFLOW_HOME=/opt/airflow
RUN mkdir -p /opt/airflow/dags /opt/airflow/logs && chmod -R g+rwX /opt/airflow
