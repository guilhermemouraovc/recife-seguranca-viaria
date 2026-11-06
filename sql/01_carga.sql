-- M3: load the cleaned + geocoded sinistros (scripts/load_postgis.sh writes the CSV).
-- geom is SIRGAS 2000 / UTM 25S (EPSG:31985) so distances are in meters and use the index.
CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS sinistros CASCADE;
CREATE TABLE sinistros (
    id serial PRIMARY KEY,
    ano_arquivo int,
    data date,
    hora time,
    gravidade text,
    tipo_acidente text,
    situacao text,
    bairro text,
    endereco text,
    numero text,
    atropelamento boolean,
    criterio_atropelamento text,  -- tipo+pedestre | tipo | pedestre | NULL (informativo)
    usuario_vulneravel text,
    vitimas int,
    vitimasfatais int,
    data_fora_do_ano_arquivo boolean,
    geo_precisao text,    -- semaforo | endereco_numero | endereco_via | semaforo_nao_confere | endereco_nao_confere | NULL
    coord_precisao text,  -- alta | media | baixa | NULL (see geocode_sinistros.py, docs/11)
    lat float8,
    lon float8,
    geom geometry(Point, 31985)
);
COMMENT ON TABLE sinistros IS
    'Chamados de sinistro CTTU 2015-2024 (dados abertos). 2015 so desde junho; chamados != numeros '
    'oficiais dos Relatorios Anuais; dez/2025 no arquivo 2024 e preliminar/suspeito; geom de trecho de '
    'rua (endereco_via) ou do semaforo, nao do ponto exato. Geocodificacao (c) colaboradores do '
    'OpenStreetMap, ODbL. Ver docs/11-base-atropelamentos.md.';

\copy sinistros (ano_arquivo, data, hora, gravidade, tipo_acidente, situacao, bairro, endereco, numero, atropelamento, criterio_atropelamento, usuario_vulneravel, vitimas, vitimasfatais, data_fora_do_ano_arquivo, geo_precisao, coord_precisao, lat, lon) FROM '/data/sinistros/sinistros_geo.csv' WITH (FORMAT csv, HEADER true)

UPDATE sinistros SET geom = ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 31985)
WHERE lat IS NOT NULL;

CREATE INDEX sinistros_geom_idx ON sinistros USING gist (geom);
CREATE INDEX sinistros_data_idx ON sinistros (data);
ANALYZE sinistros;

-- Validation sites for M4 (sql/locais_validacao.csv).
DROP TABLE IF EXISTS locais_validacao;
CREATE TABLE locais_validacao (nome text, lat float8, lon float8, data_intervencao date,
                               data_aproximada boolean, fonte text);
\copy locais_validacao FROM '/sql/locais_validacao.csv' WITH (FORMAT csv, HEADER true)
ALTER TABLE locais_validacao ADD COLUMN geom geometry(Point, 31985);
UPDATE locais_validacao SET geom = ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 31985);
