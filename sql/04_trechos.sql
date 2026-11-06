-- O2: export the risk trechos for the vehicle module (embarcados/) as one JSON array.
-- Trecho de risco = top 10% of clusters, the same cut sql/03_validacao.sql validates.
--
-- vel_segura_kmh follows docs/13-velocidade-segura.md (OMS 2023, Tabela 1): 30 km/h where
-- vulnerable users (pedestre, ciclista, moto) are in the conflict, else 50 km/h (urban
-- intersections). raio_m has a 200 m floor because the geocoding puts every sinistro of a
-- street-in-bairro at one point (radius 0 otherwise), and they can be hundreds of m off.
-- faixas = horario bands holding >= 25% of the cluster's sinistros (25% = uniform over 4 bands).
-- ponytail: 25% vulneravel, 200 m and 25% faixa are calibration knobs, not findings.
WITH vuln AS (
    SELECT c.cluster_id, avg((s.usuario_vulneravel <> 'nenhum')::int) AS pct
    FROM sinistros_clusterizados('2025-01-01') c JOIN sinistros s USING (id)
    WHERE c.cluster_id IS NOT NULL
    GROUP BY 1
), faixas AS (
    SELECT cluster_id,
           json_agg(json_build_array(split_part(faixa_horaria, '-', 1)::int,
                                     split_part(split_part(faixa_horaria, '-', 2), ' ', 1)::int)
                    ORDER BY faixa_horaria) AS faixas
    FROM (SELECT cluster_id, faixa_horaria, sum(n_sinistros) AS n,
                 sum(sum(n_sinistros)) OVER (PARTITION BY cluster_id) AS tot
          FROM risco_horario WHERE faixa_horaria <> 'sem hora' GROUP BY 1, 2) f
    WHERE n >= 0.25 * tot
    GROUP BY 1
)
SELECT json_agg(json_build_object(
           'id', t.posicao,
           'nome', split_part(t.enderecos, ' | ', 1),
           'lat', round(ST_Y(ST_Transform(ST_Centroid(t.area), 4326))::numeric, 5),
           'lon', round(ST_X(ST_Transform(ST_Centroid(t.area), 4326))::numeric, 5),
           'raio_m', greatest(200, round(ST_MaxDistance(ST_Centroid(t.area), t.area)))::int,
           'vel_segura_kmh', CASE WHEN v.pct >= 0.25 THEN 30 ELSE 50 END,
           'faixas', coalesce(f.faixas, '[[0,24]]'::json))
       ORDER BY t.posicao)
FROM risco_atual t
JOIN vuln v USING (cluster_id)
LEFT JOIN faixas f USING (cluster_id)
WHERE t.posicao <= 0.1 * t.n_clusters;
