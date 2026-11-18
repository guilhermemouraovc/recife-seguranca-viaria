# API FastAPI (seção 10). Cabeçalho idêntico ao de docker/python/Dockerfile: mesma camada de
# dependências, então o modelo treinado pelas DAGs carrega aqui com o mesmo scikit-learn.
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

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
