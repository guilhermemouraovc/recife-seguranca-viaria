#!/usr/bin/env bash
# M3/M4: start PostGIS, load the geocoded sinistros, build risk tables, run validation.
# Needs: Docker running + data/processed/sinistros/sinistros_2015_2024_geo.parquet
#        (scripts/clean_sinistros.py, then scripts/geocode_sinistros.py).
set -euo pipefail
cd "$(dirname "$0")/.."

.venv/bin/python -c "
import pandas as pd
cols = ['ano_arquivo', 'data', 'hora', 'gravidade', 'tipo_acidente', 'situacao', 'bairro', 'endereco',
        'numero', 'atropelamento', 'usuario_vulneravel', 'vitimas', 'vitimasfatais',
        'data_fora_do_ano_arquivo', 'geo_precisao', 'lat', 'lon']
pd.read_parquet('data/processed/sinistros/sinistros_2015_2024_geo.parquet')[cols].to_csv(
    'data/processed/sinistros/sinistros_geo.csv', index=False)
"

docker compose up -d --wait
psql() { docker compose exec -T db psql -U postgres -v ON_ERROR_STOP=1 -q "$@"; }
psql -f /sql/01_carga.sql
psql -f /sql/02_risco.sql
psql -c "SELECT geo_precisao, count(*) FROM sinistros GROUP BY 1 ORDER BY 2 DESC"
psql -c "SELECT posicao, n_sinistros, n_obitos, round(score) AS score, enderecos FROM risco_atual ORDER BY posicao LIMIT 15"
psql -f /sql/03_validacao.sql

# O2: risk trechos for the vehicle module; trechos.h embeds them for the Wokwi sketch.
psql -tA -f /sql/04_trechos.sql > embarcados/trechos.json
{ echo '// Gerado por scripts/load_postgis.sh (sql/04_trechos.sql). Não editar à mão.'
  echo 'const char TRECHOS_JSON[] = R"json('; cat embarcados/trechos.json; echo ')json";'
} > embarcados/simulacao/trechos.h
