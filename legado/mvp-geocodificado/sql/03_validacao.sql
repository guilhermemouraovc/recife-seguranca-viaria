-- M4 validation: each CTTU intervention site should already be a high-risk trecho
-- using only the sinistros from BEFORE its intervention date.
-- Pass = the riskiest cluster within 500 m of the site is in the top 10% of clusters.
-- 500 m, not less: endereco_via points are street-in-bairro stretches (geocode_sinistros.py),
-- so a sinistro at the site can be geocoded hundreds of meters away (Zeferino Agra: 252 m).
--
-- Runs every configuration under comparison; choosing one is a group decision (see the PR).
DROP TABLE IF EXISTS validacao_m4;
CREATE TABLE validacao_m4 AS
WITH configs (config, apenas_atropelamentos, eps_m, min_pts) AS (VALUES
    ('todos-eps100-min10', false, 100::float8, 10),
    ('atrop-eps100-min3',  true,  100::float8, 3),
    ('atrop-eps100-min4',  true,  100::float8, 4),
    ('atrop-eps100-min5',  true,  100::float8, 5)
)
SELECT cfg.config,
       l.nome,
       l.data_intervencao,
       l.data_aproximada,
       r.posicao,
       r.n_clusters,
       round(100.0 * r.posicao / r.n_clusters, 1) AS top_pct,
       r.n_sinistros,
       r.n_obitos,
       round(ST_Distance(r.area, l.geom)) AS dist_m,
       r.enderecos,
       coalesce(100.0 * r.posicao / r.n_clusters <= 10, false) AS aprovado
FROM configs cfg
CROSS JOIN locais_validacao l
LEFT JOIN LATERAL (
    SELECT * FROM risco_clusters(l.data_intervencao, eps_m => cfg.eps_m, min_pts => cfg.min_pts,
                                 apenas_atropelamentos => cfg.apenas_atropelamentos) r
    WHERE ST_DWithin(r.area, l.geom, 500)
    ORDER BY r.score DESC LIMIT 1
) r ON true;

\echo 'Validação M4 por local'
SELECT config, nome, data_intervencao, posicao, n_clusters, top_pct, n_sinistros, dist_m, aprovado
FROM validacao_m4 ORDER BY config, data_intervencao;

\echo 'Resumo: quantos dos 3 locais passam em cada configuração'
SELECT config,
       count(*) FILTER (WHERE aprovado) AS locais_aprovados,
       count(*) AS locais,
       string_agg(CASE WHEN aprovado THEN nome END, '; ' ORDER BY data_intervencao) AS aprovados
FROM validacao_m4 GROUP BY config ORDER BY config;
