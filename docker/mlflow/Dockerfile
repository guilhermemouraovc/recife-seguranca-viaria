# MLflow tracking server (ARCHITECTURE.md, seção 7): backend no Postgres, artefatos no volume
# mlflow_artifacts. As instruções até o pip install são idênticas às de docker/python/Dockerfile
# de propósito: o build reaproveita aquela camada e o servidor roda a mesma versão do mlflow que
# os clientes (tooling, jupyter, DAGs).
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

# Backend (MLFLOW_BACKEND_STORE_URI) e hosts aceitos (MLFLOW_SERVER_ALLOWED_HOSTS) vêm do compose.
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--artifacts-destination", "/mlflow/artifacts"]
