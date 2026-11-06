-- O2: export the risk trechos in EXACTLY the format of docs/09-contrato-trechos-e-telemetria.md
-- (parte 1), written by scripts/load_postgis.sh to data/contrato/trechos.json and checked by
-- scripts/validar_trechos.py.
--
-- Configuration via psql variables (load_postgis.sh passes them; defaults below):
--   m4_apenas_atropelamentos (true|false), m4_eps_m, m4_min_pts. Default = the configuration
--   chosen in docs/11 (atropelamentos, eps 100 m, min_pts 5).
-- Trecho de risco = top 10% of clusters, the same cut sql/03_validacao.sql validates.
--
-- id       'c<posicao>' (position by score; ties broken by cluster_id so ids stay unique).
-- score    cluster score / highest exported score (0-1). risco = contract bands
--          (< 0.40 baixo, 0.40-0.69 medio, >= 0.70 alto).
-- horas    every hour 0-23 of the horario bands (00-06, 06-12, 12-18, 18-24) holding >= 25% of
--          the cluster's sinistros with hora (25% = uniform over 4 bands); [] = all day
--          (no band reaches 25%, or no sinistro with hora -- e.g. 2022 has no hora at all).
-- vel_segura  docs/13-velocidade-segura.md (OMS 2023, Tabela 1): 30 km/h when vulnerable users
--          (pedestre, ciclista, moto) are in >= 25% of the cluster's sinistros, else 50 km/h.
-- raio_m   max distance from the centroid to the cluster hull, floor 200 m (endereco_via points
--          stack on one spot and can be hundreds of m off), ceiling 500 m (contract).
-- ponytail: 25% vulneravel, 25% faixa, 200 m and the top-10% cut are calibration knobs, not findings.
\if :{?m4_apenas_atropelamentos}
\else
\set m4_apenas_atropelamentos true
\endif
\if :{?m4_eps_m}
\else
\set m4_eps_m 100
\endif
\if :{?m4_min_pts}
\else
\set m4_min_pts 5
\endif

WITH cfg AS (
    SELECT :'m4_apenas_atropelamentos'::boolean AS apenas, :'m4_eps_m'::float8 AS eps_m,
           :'m4_min_pts'::int AS min_pts
), risco AS (
    SELECT r.*, row_number() OVER (ORDER BY r.score DESC, r.cluster_id) AS pos
    FROM cfg, risco_clusters('2025-01-01', eps_m => cfg.eps_m, min_pts => cfg.min_pts,
                             apenas_atropelamentos => cfg.apenas) r
), top AS (
    SELECT * FROM risco WHERE posicao <= 0.1 * n_clusters AND pos <= 200  -- contract: max 200 trechos
), membros AS (
    SELECT c.cluster_id, c.hora, s.usuario_vulneravel
    FROM cfg, sinistros_clusterizados('2025-01-01', cfg.eps_m, cfg.min_pts, cfg.apenas) c
    JOIN sinistros s USING (id)
    WHERE c.cluster_id IN (SELECT cluster_id FROM top)
), vuln AS (
    SELECT cluster_id, avg((usuario_vulneravel <> 'nenhum')::int) AS pct FROM membros GROUP BY 1
), faixas AS (
    SELECT cluster_id, (extract(hour FROM hora)::int / 6) * 6 AS inicio, count(*) AS n,
           sum(count(*)) OVER (PARTITION BY cluster_id) AS tot
    FROM membros WHERE hora IS NOT NULL GROUP BY 1, 2
), horas AS (
    SELECT f.cluster_id, json_agg(h ORDER BY h) AS horas
    FROM faixas f CROSS JOIN LATERAL generate_series(f.inicio, f.inicio + 5) h
    WHERE f.n >= 0.25 * f.tot
    GROUP BY 1
), trechos AS (
    SELECT t.pos,
           'c' || t.pos AS id,
           left(coalesce(nullif(split_part(t.enderecos, ' | ', 1), ''), 'Trecho c' || t.pos), 60) AS nome,
           round(ST_Y(ST_Transform(ST_Centroid(t.area), 4326))::numeric, 5) AS lat,
           round(ST_X(ST_Transform(ST_Centroid(t.area), 4326))::numeric, 5) AS lon,
           least(500, greatest(200, round(ST_MaxDistance(ST_Centroid(t.area), t.area))))::int AS raio_m,
           round((t.score / max(t.score) OVER ())::numeric, 3) AS score,
           coalesce(h.horas, '[]'::json) AS horas,
           CASE WHEN v.pct >= 0.25 THEN 30 ELSE 50 END AS vel_segura
    FROM top t
    JOIN vuln v USING (cluster_id)
    LEFT JOIN horas h USING (cluster_id)
)
SELECT json_build_object(
    'versao', 1,
    'gerado_em', to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD"T"HH24:MI:SS') || '-03:00',
    'fonte', 'm4-dbscan-' || CASE WHEN (SELECT apenas FROM cfg) THEN 'atrop' ELSE 'todos' END
             || '-eps' || :'m4_eps_m' || '-min' || :'m4_min_pts',
    'trechos', coalesce((
        SELECT json_agg(json_build_object(
                   'id', id, 'nome', nome, 'lat', lat, 'lon', lon, 'raio_m', raio_m,
                   'risco', CASE WHEN score >= 0.70 THEN 'alto' WHEN score >= 0.40 THEN 'medio' ELSE 'baixo' END,
                   'score', score, 'horas', horas, 'vel_segura', vel_segura)
               ORDER BY pos)
        FROM trechos), '[]'::json)
);
