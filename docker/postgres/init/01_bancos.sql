-- Roda uma vez, quando o volume pgdata é criado. Um banco por consumidor no mesmo servidor:
-- o banco do POSTGRES_DB fica com os dados da solução e o mlflow guarda o backend do MLflow.
CREATE DATABASE mlflow;
