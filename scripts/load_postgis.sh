#!/usr/bin/env bash
# M3/M4: start PostGIS, load the geocoded sinistros, build risk tables, run validation,
# export the risk trechos in the docs/09 contract format to data/contrato/trechos.json.
# Needs: Docker running + data/processed/sinistros/sinistros_2015_2024_geo.parquet
#        (scripts/clean_sinistros.py, then scripts/geocode_sinistros.py).
# Configuration of the exported trechos: default = atrop-eps100-min5, chosen from
# sql/03_validacao.sql (docs/11, "Validação do M4 e configuração escolhida"). Override with e.g.
#   M4_APENAS_ATROPELAMENTOS=false M4_EPS_M=100 M4_MIN_PTS=10 scripts/load_postgis.sh
set -euo pipefail
cd "$(dirname "$0")/.."

.venv/bin/python -c "
import pandas as pd
cols = ['ano_arquivo', 'data', 'hora', 'gravidade', 'tipo_acidente', 'situacao', 'bairro', 'endereco',
        'numero', 'atropelamento', 'criterio_atropelamento', 'usuario_vulneravel', 'vitimas', 'vitimasfatais',
        'data_fora_do_ano_arquivo', 'geo_precisao', 'coord_precisao', 'lat', 'lon']
pd.read_parquet('data/processed/sinistros/sinistros_2015_2024_geo.parquet')[cols].to_csv(
    'data/processed/sinistros/sinistros_geo.csv', index=False)
"

docker compose up -d --wait
psql() { docker compose exec -T db psql -U postgres -v ON_ERROR_STOP=1 -q "$@"; }
psql -f /sql/01_carga.sql
psql -f /sql/02_risco.sql
psql -c "SELECT geo_precisao, coord_precisao, count(*) FROM sinistros GROUP BY 1, 2 ORDER BY 3 DESC"
psql -c "SELECT posicao, n_sinistros, n_obitos, round(score) AS score, enderecos FROM risco_atual ORDER BY posicao LIMIT 15"
psql -f /sql/03_validacao.sql

# O2: risk trechos for the vehicle module and the panel (docs/09, parte 1).
mkdir -p data/contrato
psql -tA \
    -v m4_apenas_atropelamentos="${M4_APENAS_ATROPELAMENTOS:-true}" \
    -v m4_eps_m="${M4_EPS_M:-100}" \
    -v m4_min_pts="${M4_MIN_PTS:-5}" \
    -f /sql/04_trechos.sql > data/contrato/trechos.json
.venv/bin/python scripts/validar_trechos.py data/contrato/trechos.json
