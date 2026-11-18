# JupyterLab para os notebooks (profile dev). As instruções até o pip install são idênticas às de
# docker/python/Dockerfile de propósito: o build reaproveita aquela camada e os notebooks rodam
# com as mesmas versões do resto da solução.
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

# O token vem de JUPYTER_TOKEN (variável lida pelo próprio Jupyter Server).
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--ServerApp.root_dir=/app"]
