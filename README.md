# Antecipa Recife

O nome vem da entrevista com a CTTU: o desafio apontado foi **antecipar o próximo sinistro**. A
solução prevê os locais de maior risco no trimestre seguinte para a prefeitura agir antes.

Solução de Aprendizado de Máquina (CESAR School, 2026.6) que prevê **quais locais do Recife têm
maior risco de acidente com vítima no próximo trimestre** e entrega esse ranking para a CTTU por
API e dashboard. A fonte é o dataset público de acidentes de trânsito da Prefeitura do Recife
(2015–2024). O desenho completo da solução está no [`ARCHITECTURE.md`](ARCHITECTURE.md), que é a
fonte da verdade da trilha de AM.

- **Site do projeto:** https://sites.google.com/cesar.school/seguranca-viaria-recife-g3?usp=sharing

## Integrantes

| Nome | GitHub |
|---|---|
| Guilherme Mourão Vieira Coelho | [guilhermemouraovc](https://github.com/guilhermemouraovc) |
| João Antonio Sampaio Ferreira | [Jooaosampaio](https://github.com/Jooaosampaio) |
| Lavínia Maranhão Faria Silva | [lavasilva](https://github.com/lavasilva) |
| Luiz Felipe Soriano | [lfelipesbs](https://github.com/lfelipesbs) |
| Maria Clara Neves | [claranevess](https://github.com/claranevess) |
| Marina Hoffmann Guimarães | [marinaghoffmann](https://github.com/marinaghoffmann) |
| Rodrigo de Barros Lima Tenório | [RodrigoBLT](https://github.com/RodrigoBLT) |
| Vinícius Bernardo da Silva | [Vinib80](https://github.com/Vinib80) |

## Estado atual

Tudo abaixo roda hoje e sobe com `docker compose up`:

- **Ingestão e preparo** (`src/ingestao/`, `src/preparo/`): baixa os 10 CSVs anuais (2015–2024)
  do dataset `acidentes-de-transito-com-e-sem-vitimas` pela API CKAN do Portal de Dados Abertos
  do Recife, com proveniência em `data/manifest.jsonl` (SHA-256, data, origem); unifica o esquema
  dos 10 anos, limpa, identifica cada local por bairro + logradouro normalizados (`local_id`) e
  monta a tabela `features` (local × trimestre, com o alvo do trimestre seguinte) no Postgres e em
  Parquet. Um teste garante que nenhuma feature usa dado do futuro.
- **EDA** (`notebooks/01_eda_bootstrap.ipynb`, `02_preparacao_features.ipynb`), com as figuras em
  `reports/figuras/eda/`.
- **Modelagem com MLflow** (`src/modelagem/`): 6 modelos (Regressão Logística, KNN, Árvore de
  Decisão, Random Forest, AdaBoost e MLP) mais a heurística de recorrência, com validação temporal,
  Optuna e os três experimentos `01_baseline`, `02_comparacao_modelos` e
  `03_otimizacao_hiperparametros`. O campeão é o **Random Forest**, registrado como
  `risco-viario@champion`: **PR-AUC 0,695 no teste de 2024**, contra 0,682 da Regressão Logística
  e 0,648 da heurística. Os números do treino oficial estão em `reports/resultados/`.
- **3 DAGs no Airflow 3** (`dags/`): `dag_ingestao_preparo`, `dag_treino` e `dag_scoring`.
- **Embarcado**: simulador do módulo veicular publicando em `viario/telemetria` (MQTT) e ingestor
  gravando a telemetria no Postgres (`embedded/`, `src/ingestao/telemetria.py`).
- **API FastAPI** (`api/`), com OpenAPI em `/docs`, e **dashboard Streamlit** (`app/`), com 5 abas.

## Como executar

Pré-requisitos: Docker com Compose v2 (no Windows, Docker Desktop com WSL2) e **pelo menos 8 GB
de memória para o Docker** (no Docker Desktop: Settings > Resources). Com 4 GB, as tarefas de
preparo e treino são mortas por falta de memória. Não é preciso Python, venv nem nenhuma
biblioteca no host.

**1. Configure o `.env`** (uma vez):

```bash
cp .env.example .env              # PowerShell: Copy-Item .env.example .env
```

Troque `POSTGRES_PASSWORD`, `MQTT_PASSWORD`, `JUPYTER_TOKEN`, `AIRFLOW_ADMIN_PASSWORD` e
`AIRFLOW_JWT_SECRET`. A senha do Postgres entra na URI do MLflow, então evite `@ : / ? # %` nela.
No Linux, ponha em `AIRFLOW_UID` a saída de `id -u`, para os arquivos gravados em `data/` e
`notebooks/` ficarem com o seu usuário. No Windows e no macOS, deixe `50000`. No macOS, a porta
5000 costuma estar ocupada pelo AirPlay: troque `MLFLOW_PORT` para `5001`.

**2. Suba a solução:**

```bash
docker compose up -d              # sobe todos os serviços em segundo plano
docker compose ps                 # espere todos ficarem "healthy" (cerca de 1 min depois do build)
```

Na primeira vez, o `up` monta as imagens a partir do `requirements.txt`, o que leva alguns
minutos; as imagens Python compartilham a camada das dependências, então ela é instalada uma vez
só. Depois de mudar o `requirements.txt`, rode `docker compose build`. Mudanças em `src/`,
`dags/`, `api/`, `app/`, `tests/` e `notebooks/` não exigem rebuild, porque entram nos containers
por bind mount.

**3. Rode o pipeline.** As DAGs nascem pausadas. Em http://localhost:8080 (login
`AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD`), ative as três DAGs:

1. `dag_ingestao_preparo` (cerca de 1 min) baixa os CSVs e publica a tabela `features`;
2. a publicação dispara sozinha a `dag_treino` (cerca de 35 min), que treina, compara, otimiza e
   registra o campeão no MLflow;
3. depois do treino, acione a `dag_scoring` (botão Trigger; menos de 1 min), que grava os scores
   que a API e o dashboard mostram.

**4. Use:**

| O quê | Endereço | Acesso |
|---|---|---|
| Dashboard | http://localhost:8501 | livre |
| API (documentação OpenAPI) | http://localhost:8000/docs | livre |
| Airflow | http://localhost:8080 | `AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD` |
| MLflow | http://localhost:5000 (`MLFLOW_PORT`) | livre |
| JupyterLab (profile `dev`) | http://localhost:8888 | token `JUPYTER_TOKEN` |

**Outros comandos:**

```bash
docker compose --profile dev up jupyter                        # notebooks em http://localhost:8888
docker compose run --rm tooling pytest                         # roda os testes
docker compose run --rm tooling python -m src.ingestao.fetch_datasets   # etapas do pipeline à mão, sem o Airflow:
docker compose run --rm tooling python -m src.preparo.clean_sinistros   #   baixa, limpa,
docker compose run --rm tooling python -m src.preparo.local_id          #   local_id e dim_local (staging),
docker compose run --rm tooling python -m src.preparo.features          #   tabela features (staging),
docker compose run --rm tooling python -m src.preparo.publicar          #   publica o staging,
docker compose run --rm tooling python -m src.modelagem.treino          #   treina e registra o campeão
docker compose run --rm tooling python -m src.modelagem.exportar        # exporta os números do treino para reports/resultados/
docker compose down -v                                         # derruba tudo e apaga os volumes
```

O banco `mlflow` e o banco `airflow` são criados só quando o volume `pgdata` nasce. Se você já
tinha subido o Postgres antes desta versão, rode `docker compose down -v` uma vez.

O `fetch_datasets` aceita `--force` para baixar de novo mesmo o que não mudou.

### Serviços e portas

| Serviço | Imagem | Porta no host | Papel |
|---|---|---|---|
| `postgres` | `postgres:16` | `5433` (`POSTGRES_PORT`) | bancos `viario` (dados da solução), `mlflow` e `airflow`; volume nomeado `pgdata` |
| `mosquitto` | `eclipse-mosquitto:2` | `1883` (`MQTT_PORT`) | broker MQTT; login com `MQTT_USER`/`MQTT_PASSWORD`, sem acesso anônimo |
| `mlflow` | `docker/mlflow/Dockerfile` | `5000` (`MLFLOW_PORT`) | tracking server e Model Registry; artefatos no volume nomeado `mlflow_artifacts` |
| `airflow-init` | `docker/airflow/Dockerfile` | nenhuma | migra o banco do Airflow e termina |
| `airflow-api-server` | `docker/airflow/Dockerfile` | `8080` (`AIRFLOW_PORT`) | UI e API do Airflow 3.4.0 |
| `airflow-scheduler` | `docker/airflow/Dockerfile` | nenhuma | agenda e executa as tarefas (`LocalExecutor`) |
| `airflow-dag-processor` | `docker/airflow/Dockerfile` | nenhuma | lê os arquivos de `dags/` |
| `api` | `docker/api/Dockerfile` | `8000` (`API_PORT`) | FastAPI; documentação em `/docs` |
| `dashboard` | `docker/dashboard/Dockerfile` | `8501` (`DASHBOARD_PORT`) | Streamlit |
| `ingestor` | `docker/ingestor/Dockerfile` | nenhuma | assina `viario/telemetria` e grava no Postgres |
| `simulador` | `docker/simulador/Dockerfile` | nenhuma | módulo veicular simulado; publica em `viario/telemetria` |
| `jupyter` | `docker/jupyter/Dockerfile` | `8888` (`JUPYTER_PORT`) | JupyterLab para `notebooks/` (profile `dev`, não sobe no `up`) |
| `tooling` | `docker/python/Dockerfile` | nenhuma | pipeline à mão e testes via `docker compose run --rm` (profile `tooling`, não sobe no `up`) |

Dentro da rede do compose, os serviços se acham pelo nome: `postgres:5432`, `mosquitto:1883`,
`http://mlflow:5000`, `http://api:8000`, `http://airflow-api-server:8080`.

### O que cada etapa gera

| Caminho | Conteúdo | Versionado |
|---|---|---|
| `data/raw/cttu/acidentes-de-transito-com-e-sem-vitimas/*.csv` | os 10 CSVs anuais, como vieram do portal | não |
| `data/manifest.jsonl` | proveniência de cada download | sim |
| `data/processed/sinistros/sinistros_2015_2024.parquet` | uma linha por chamado de sinistro, esquema unificado | não |
| `data/processed/sinistros/colunas_por_ano.json` | colunas encontradas em cada CSV anual | não |
| `data/processed/sinistros/README.md` | ressalvas da fonte, contagens por ano e duplicados removidos | não |
| `data/processed/acidentes_local.parquet` | acidentes que contam (sem `CANCELADA`/`DUPLICIDADE`), com `local_id` e `trimestre` | não |
| `data/processed/dim_local.parquet` e tabela `dim_local` | um local por linha: `local_id`, bairro e logradouro legíveis | não |
| `data/processed/local_id_resumo.json` | exclusões, nº de locais e distribuição de acidentes por local | não |
| `data/processed/features.parquet` e tabela `features` | local × trimestre (locais com ≥ 3 acidentes), features e alvo `y` | não |
| `data/processed/modelagem/` | snapshot das features e estado de cada etapa do treino | não |
| `data/processed/scores.parquet` e tabela `scores` | score de cada local para o trimestre seguinte | não |
| `reports/resultados/` | métricas do treino oficial e gráficos do campeão | sim |

### Ressalvas da fonte que já estão tratadas

- A coluna `timestamp` do dicionário do portal não existe nos CSVs; o nome real é `data`
  (`DATA` em 2018–2019).
- `hora` está vazia em todo o CSV de 2022 e não é recuperável de outra coluna.
- `acidente_verificado` só existe de 2018 em diante. Não é usada como filtro: vira categórica
  com `DESCONHECIDO`.
- `endereco_cruzamento`, `numero_cruzamento` e `referencia_cruzamento` só existem de 2016 a 2019.
- As flags `DUPLICIDADE` e `CANCELADA` continuam na coluna `situacao`.

A lista completa sai no README gerado em `data/processed/sinistros/`.

## Estrutura do repositório

```
.
├── ARCHITECTURE.md          # desenho da solução de AM (fonte da verdade)
├── docker-compose.yml       # postgres, mosquitto, mlflow, airflow, api, dashboard, ingestor, simulador, jupyter e tooling
├── .env.example             # variáveis do compose (copie para .env)
├── requirements.txt         # dependências Python com versões travadas (ARCHITECTURE.md, seção 14)
├── docker/                  # um Dockerfile por serviço, mosquitto.conf e init do Postgres
├── notebooks/               # 01_eda_bootstrap, 02_preparacao_features e modelo_* (investigação de cada modelo)
├── src/
│   ├── ingestao/            # ckan_client, manifest, fetch_datasets, telemetria (ingestor MQTT)
│   ├── preparo/             # clean_sinistros, local_id, features
│   ├── modelagem/           # pipeline, validacao, metricas, treino (MLflow), scoring
│   └── comum/               # conexão com o Postgres e cliente MQTT
├── dags/                    # dag_ingestao_preparo, dag_treino, dag_scoring
├── api/                     # FastAPI
├── app/                     # dashboard Streamlit
├── embedded/
│   ├── simulador/           # módulo veicular simulado (publica em viario/telemetria)
│   └── esp32/               # README do módulo ESP32 (payload MQTT com local_id)
├── tests/                   # pytest
├── reports/                 # figuras/ (EDA, modelos e sistema) e resultados/ do treino oficial
├── data/                    # raw/ e processed/ fora do git; manifest.jsonl versionado
├── legado/mvp-geocodificado/ # MVP anterior (Nominatim + PostGIS), fora da solução atual
└── legado/projeto6/         # docs/ e pesquisa-qualitativa/ do Projeto 6
```

## Legado e histórico

O MVP anterior, baseado em geocodificação (Nominatim + PostGIS e contrato de trechos lat/lon),
foi movido sem apagar para `legado/mvp-geocodificado/`. O README de lá explica o porquê.

O material do Projeto 6 que dividia este repositório (`docs/`, `pesquisa-qualitativa/`) foi
movido sem alteração para `legado/projeto6/`. As configurações de agentes de IA (`.github/`,
`.agents`, `.codex`, `.cursor`, `.goose`, `.grok`, `.kimi-code`, `.omp`) foram removidas e
seguem só no histórico do git. `CLAUDE.md` e `.claude/`
são configuração local de quem usa o Claude Code e estão no `.gitignore`.

## Origem dos dados

Portal de Dados Abertos do Recife (CKAN), dataset
[`acidentes-de-transito-com-e-sem-vitimas`](https://dados.recife.pe.gov.br/dataset/acidentes-de-transito-com-e-sem-vitimas),
licença ODbL. São **chamados** registrados pela CTTU, que podem divergir dos números dos
relatórios anuais oficiais. 2015 só tem dados a partir de junho.
