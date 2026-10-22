-- M4 validation: each CTTU intervention site should already be a high-risk trecho
-- using only the sinistros from BEFORE its intervention date.
-- Pass = the riskiest cluster within 500 m of the site is in the top 10% of clusters.
-- 500 m, not less: points are street-in-bairro centroids (geocode_sinistros.py), so a
-- sinistro at the site can be geocoded hundreds of meters away (Zeferino Agra: 252 m).
SELECT l.nome,
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
FROM locais_validacao l
LEFT JOIN LATERAL (
    SELECT * FROM risco_clusters(l.data_intervencao) r
    WHERE ST_DWithin(r.area, l.geom, 500)
    ORDER BY r.score DESC LIMIT 1
) r ON true
ORDER BY l.data_intervencao;
