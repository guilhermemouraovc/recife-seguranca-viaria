# Imagem Python da trilha de AM, construída a partir do requirements.txt da raiz.
# Nesta rodada serve ao serviço `tooling` (ingestão, preparo e testes); o código entra por
# bind mount no docker-compose.yml, então mudança em src/ ou tests/ não exige rebuild.
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
