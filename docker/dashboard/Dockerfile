# Dashboard Streamlit (seção 11). Cabeçalho idêntico ao de docker/python/Dockerfile.
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

CMD ["streamlit", "run", "app/dashboard.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
