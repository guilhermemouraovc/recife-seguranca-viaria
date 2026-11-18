-- Roda uma vez, quando o volume pgdata é criado. Um banco por consumidor no mesmo servidor:
-- o banco do POSTGRES_DB fica com os dados da solução, o mlflow guarda o backend do MLflow e o
-- airflow guarda os metadados do Airflow (seção 12).
CREATE DATABASE mlflow;
CREATE DATABASE airflow;
