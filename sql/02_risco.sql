-- M4: recurrence by trecho (spatial cluster) and horario, combined into a risk score.
--
-- Gravidade weight = UPS (Unidade Padrão de Severidade, DENATRAN 1987): so danos 1,
-- com feridos 4, com feridos e pedestre (atropelamento) 6, com morte 13.
-- Recencia: each sinistro weighs 0.5^(idade/meia_vida). Frequencia: the sum itself.
-- score = SUM(ups * 0.5^(idade_anos / meia_vida_anos)), only sinistros before `ref`.
--
-- Parameters: eps_m / min_pts (DBSCAN), apenas_atropelamentos (true = only rows with the
-- `atropelamento` flag, i.e. tipo ATROPELAMENTO*, animals excluded). The final configuration
-- is chosen from sql/03_validacao.sql, not here.
--
-- Excluded: CANCELADA/DUPLICIDADE, dates outside the file year, and every coordinate that is
-- not coord_precisao alta (semaforo, endereco_numero) or media (endereco_via) -- i.e. the
-- *_nao_confere ones, whose bairro or street don't match (docs/11). Clusters are only as
-- precise as the geocoding: an endereco_via point is a stretch of the street in the bairro,
-- and every sinistro of that street+bairro sits on the same point ("pilhas").

DROP FUNCTION IF EXISTS risco_clusters(date, float8, int, float8);
DROP FUNCTION IF EXISTS sinistros_clusterizados(date, float8, int);
DROP FUNCTION IF EXISTS risco_por_horario(date, float8, int, boolean);

CREATE OR REPLACE FUNCTION sinistros_clusterizados(ref date, eps_m float8 DEFAULT 100, min_pts int DEFAULT 10,
                                                   apenas_atropelamentos boolean DEFAULT false)
RETURNS TABLE (id int, cluster_id int, data date, hora time, ups int, obito boolean, geom geometry)
LANGUAGE sql STABLE AS $$
    SELECT s.id,
           ST_ClusterDBSCAN(s.geom, eps_m, min_pts) OVER () AS cluster_id,
           s.data, s.hora,
           CASE WHEN s.gravidade = 'VÍTIMA FATAL' OR s.vitimasfatais > 0 THEN 13
                WHEN s.gravidade = 'COM VÍTIMA' AND s.atropelamento THEN 6
                WHEN s.gravidade = 'COM VÍTIMA' THEN 4
                ELSE 1 END,
           s.gravidade = 'VÍTIMA FATAL' OR coalesce(s.vitimasfatais, 0) > 0,
           s.geom
    FROM sinistros s
    WHERE s.geom IS NOT NULL
      AND s.coord_precisao IN ('alta', 'media')
      AND (NOT apenas_atropelamentos OR s.atropelamento)
      AND s.data < ref
      AND NOT s.data_fora_do_ano_arquivo
      AND s.situacao IS DISTINCT FROM 'CANCELADA'
      AND s.situacao IS DISTINCT FROM 'DUPLICIDADE'
$$;

CREATE OR REPLACE FUNCTION risco_clusters(ref date, eps_m float8 DEFAULT 100, min_pts int DEFAULT 10,
                                          meia_vida_anos float8 DEFAULT 2,
                                          apenas_atropelamentos boolean DEFAULT false)
RETURNS TABLE (cluster_id int, n_sinistros bigint, n_obitos bigint, ups bigint, score float8,
               posicao bigint, n_clusters bigint, enderecos text, area geometry)
LANGUAGE sql STABLE AS $$
    WITH agg AS (
        SELECT c.cluster_id,
               count(*) AS n_sinistros,
               count(*) FILTER (WHERE c.obito) AS n_obitos,
               sum(c.ups) AS ups,
               sum(c.ups * power(0.5, (ref - c.data) / 365.25 / meia_vida_anos)) AS score,
               (SELECT string_agg(e, ' | ') FROM (
                    SELECT s.endereco AS e FROM sinistros s
                    WHERE s.id = ANY (array_agg(c.id)) AND s.endereco IS NOT NULL
                    GROUP BY s.endereco ORDER BY count(*) DESC LIMIT 3) top) AS enderecos,
               ST_ConvexHull(ST_Collect(c.geom)) AS area
        FROM sinistros_clusterizados(ref, eps_m, min_pts, apenas_atropelamentos) c
        WHERE c.cluster_id IS NOT NULL
        GROUP BY c.cluster_id
    )
    SELECT cluster_id, n_sinistros, n_obitos, ups, score,
           rank() OVER (ORDER BY score DESC), count(*) OVER (), enderecos, area
    FROM agg
$$;

-- Cluster x dia da semana x faixa horaria, for any configuration.
CREATE OR REPLACE FUNCTION risco_por_horario(ref date, eps_m float8 DEFAULT 100, min_pts int DEFAULT 10,
                                         apenas_atropelamentos boolean DEFAULT false)
RETURNS TABLE (cluster_id int, dia_semana text, faixa_horaria text, n_sinistros bigint, ups bigint,
               pct_do_cluster numeric)
LANGUAGE sql STABLE AS $$
    SELECT c.cluster_id,
           CASE extract(isodow FROM c.data)::int
                WHEN 1 THEN 'seg' WHEN 2 THEN 'ter' WHEN 3 THEN 'qua' WHEN 4 THEN 'qui'
                WHEN 5 THEN 'sex' WHEN 6 THEN 'sab' ELSE 'dom' END,
           CASE WHEN c.hora IS NULL THEN 'sem hora'
                WHEN c.hora < '06:00' THEN '00-06 madrugada'
                WHEN c.hora < '12:00' THEN '06-12 manha'
                WHEN c.hora < '18:00' THEN '12-18 tarde'
                ELSE '18-24 noite' END,
           count(*),
           sum(c.ups),
           round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY c.cluster_id), 1)
    FROM sinistros_clusterizados(ref, eps_m, min_pts, apenas_atropelamentos) c
    WHERE c.cluster_id IS NOT NULL
    GROUP BY 1, 2, 3
$$;

-- Current snapshot with the default configuration (todos, eps 100, min_pts 10) for exploration/maps.
DROP TABLE IF EXISTS risco_atual;
CREATE TABLE risco_atual AS SELECT * FROM risco_clusters('2025-01-01');
CREATE INDEX ON risco_atual USING gist (area);

DROP TABLE IF EXISTS risco_horario;
CREATE TABLE risco_horario AS SELECT * FROM risco_por_horario('2025-01-01');
