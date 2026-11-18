-- M6: detalhe de cada trecho para o painel (abas Mapa e Detalhe), escrito por
-- scripts/load_postgis.sh em painel/detalhe.json. NÃO faz parte do contrato docs/09 (o módulo
-- veicular não lê isto): é só o painel, por isso fica fora de data/contrato/.
--
-- Mesma seleção e mesmos ids do sql/04_trechos.sql (mesmas variáveis m4_*; o CTE risco/top
-- é cópia de lá -- se mudar um, mude o outro). Por trecho:
--   n_sinistros, n_com_vitima (COM VÍTIMA ou fatal), n_obitos, posicao/n_clusters
--   envolvidos  usuario_vulneravel: moto/pedestre/ciclista/nenhum. Envolvido NÃO é vítima.
--   por_ano     [ano, total, com_vitima]. 2015 só jun-dez; queda a partir de 2020 é registro.
--   semana      7 dias (seg..dom) x 4 faixas (0-6, 6-12, 12-18, 18-24); sem_hora fica fora.
-- Só sinistros antes de 2025-01-01 (dez/2025 suspeito e 2025 preliminar ficam fora, docs/06).
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
    SELECT * FROM risco WHERE posicao <= 0.1 * n_clusters AND pos <= 200
), m AS (
    SELECT t.pos, c.data, c.hora, c.obito,
           c.obito OR s.gravidade = 'COM VÍTIMA' AS com_vitima, s.usuario_vulneravel
    FROM cfg, sinistros_clusterizados('2025-01-01', cfg.eps_m, cfg.min_pts, cfg.apenas) c
    JOIN sinistros s USING (id)
    JOIN top t USING (cluster_id)
), resumo AS (
    SELECT pos, count(*) AS n, count(*) FILTER (WHERE com_vitima) AS cv,
           count(*) FILTER (WHERE obito) AS ob, count(*) FILTER (WHERE hora IS NULL) AS sem_hora,
           json_build_object(
               'moto', count(*) FILTER (WHERE usuario_vulneravel = 'moto'),
               'pedestre', count(*) FILTER (WHERE usuario_vulneravel = 'pedestre'),
               'ciclista', count(*) FILTER (WHERE usuario_vulneravel = 'ciclista'),
               'nenhum', count(*) FILTER (WHERE usuario_vulneravel = 'nenhum')) AS envolvidos
    FROM m GROUP BY pos
), ano AS (
    SELECT pos, json_agg(json_build_array(a, total, cv) ORDER BY a) AS por_ano
    FROM (SELECT pos, extract(year FROM data)::int AS a, count(*) AS total,
                 count(*) FILTER (WHERE com_vitima) AS cv
          FROM m GROUP BY 1, 2) x
    GROUP BY pos
), semana AS (
    -- grade completa 7x4 (zeros incluídos), dia 1 = segunda
    SELECT t.pos, json_agg(linha ORDER BY d) AS semana
    FROM top t CROSS JOIN generate_series(1, 7) d
    CROSS JOIN LATERAL (
        SELECT json_agg((SELECT count(*) FROM m
                         WHERE m.pos = t.pos AND m.hora IS NOT NULL
                           AND extract(isodow FROM m.data) = d
                           AND extract(hour FROM m.hora)::int / 6 = f) ORDER BY f) AS linha
        FROM generate_series(0, 3) f) l
    GROUP BY t.pos
)
SELECT json_build_object(
    'fonte', 'm4-dbscan-' || CASE WHEN (SELECT apenas FROM cfg) THEN 'atrop' ELSE 'todos' END
             || '-eps' || :'m4_eps_m' || '-min' || :'m4_min_pts',
    'n_clusters', (SELECT max(n_clusters) FROM top),
    'trechos', coalesce((
        SELECT json_object_agg('c' || t.pos, json_build_object(
                   'posicao', t.pos, 'n_sinistros', r.n, 'n_com_vitima', r.cv, 'n_obitos', r.ob,
                   'sem_hora', r.sem_hora, 'envolvidos', r.envolvidos, 'por_ano', a.por_ano,
                   'semana', s.semana) ORDER BY t.pos)
        FROM top t JOIN resumo r USING (pos) JOIN ano a USING (pos) JOIN semana s USING (pos)), '{}'::json)
);
