# Legado: MVP geocodificado

Esta pasta guarda o MVP de "trechos de risco" construído antes da arquitetura atual da trilha
de Aprendizado de Máquina. Ele foi **movido, não apagado**: é entrega da outra trilha do
Projeto 6 e o histórico de cada arquivo continua no git (`git log --follow <arquivo>`).

## Por que saiu

O [`ARCHITECTURE.md`](../../ARCHITECTURE.md) (seção 2.3 e seção 15) descarta a abordagem
geocodificada:

- **Não existe latitude nem longitude no dado de sinistros.** O MVP inferia coordenadas via
  Nominatim (OpenStreetMap) e semáforos, com precisão variável. A solução atual identifica o
  local só por texto (`local_id` = bairro + logradouro normalizados).
- **Sem banco espacial.** PostGIS, clusters espaciais e o contrato de trechos lat/lon não fazem
  parte da solução. O banco agora é `postgres:16` puro.
- **Sem extração de PDF.** `pdfplumber` saiu das dependências.
- **A unidade de análise mudou** de "trecho × faixa horária" para `local_id × trimestre`
  (seção 3.1), porque `hora` está vazia em todo o CSV de 2022.

Nenhum arquivo daqui pode ser importado pelo código novo, nem entrar no `docker-compose.yml`
ou no `requirements.txt`.

## O que está aqui

O layout espelha os caminhos originais na raiz do repositório:

| Caminho original | O que era |
|---|---|
| `scripts/geocode_sinistros.py`, `data/geocode/` | geocodificação via semáforo/Nominatim e cache das consultas |
| `tests/test_geocode_sinistros.py` | teste da geocodificação |
| `scripts/load_postgis.sh`, `sql/01–04`, `sql/locais_validacao.csv` | carga no PostGIS, score de risco por cluster e validação contra locais da CTTU |
| `scripts/validar_trechos.py`, `data/contrato/` | validador e arquivos de trechos no contrato lat/lon (`legado/projeto6/docs/09`) |
| `api/` | FastAPI do MVP (`/saude`, `/trechos`, `/modulo/trechos`) |
| `web/`, `scripts/build_dashboard_data.py` | dashboard estático exploratório |
| `scripts/fetch_pdfs.py`, `scripts/extract_pdfs.py`, `scripts/extract_adhoc.py` | download e extração de PDFs (pdfplumber) |
| `scripts/ontologia_grafo.py` | grafo da ontologia de `legado/projeto6/docs/03` |

O `compose.yml` com `postgis/postgis` que o `load_postgis.sh` usava foi substituído pelo
`docker-compose.yml` da raiz, então esses scripts **não rodam mais como estão**. Para
reproduzir o MVP, faça checkout de um commit anterior a esta mudança (por exemplo, `547ab86`
na `master`).

`painel/` (painel do MVP com mapa e aba do módulo veicular), `scripts/simular_modulo.py`,
`sql/05_painel.sql` e `tests/test_api.py` vieram da `master` (PRs #6 e #8) e foram movidos
para cá junto com a `api/` que eles usam. Os testes rodam de dentro desta pasta:
`cd legado/mvp-geocodificado && python -m pytest tests`.

## Documentação do MVP

Os documentos que descreviam este MVP estão em `legado/projeto6/docs/`, principalmente
`09-contrato-trechos-e-telemetria.md` e `11-base-atropelamentos.md`.
