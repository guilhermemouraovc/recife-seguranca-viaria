# TODO: nome criativo da solução

Solução de Aprendizado de Máquina (CESAR School, 2026.6) que vai prever **quais locais do
Recife têm maior risco de acidente com vítima no próximo trimestre** e entregar esse ranking
para a CTTU por API e dashboard. A fonte é o dataset público de acidentes de trânsito da
Prefeitura do Recife (2015–2024). O desenho completo da solução está no
[`ARCHITECTURE.md`](ARCHITECTURE.md), que é a fonte da verdade da trilha de AM.

- **Site do projeto:** TODO: link do Google Sites

## Integrantes

| Nome | GitHub |
|---|---|
| TODO: nome e sobrenome | TODO: @usuario |
| TODO: nome e sobrenome | TODO: @usuario |
| TODO: nome e sobrenome | TODO: @usuario |

## Estado atual

O que existe e roda hoje:

- **Ingestão** (`src/ingestao/`): baixa os 10 CSVs anuais (2015–2024) do dataset
  `acidentes-de-transito-com-e-sem-vitimas` pela API CKAN do Portal de Dados Abertos do
  Recife. Cada download fica registrado em `data/manifest.jsonl` (SHA-256, data, origem), e
  arquivos que não mudaram não são baixados de novo.
- **Preparo** (`src/preparo/clean_sinistros.py`): unifica o esquema dos 10 anos
  (`normalizar_schema`), remove duplicados exatos, padroniza tipos e texto e grava um Parquet
  único com as ressalvas da fonte documentadas.
- **Docker**: PostgreSQL 16, broker MQTT (Mosquitto, com usuário e senha) e servidor MLflow
  (backend no Postgres, artefatos em volume), todos com healthcheck; JupyterLab no profile
  `dev`; e um serviço `tooling` para rodar ingestão, preparo e testes. Nada depende de Python
  instalado no host.

O que ainda não existe e entra nas próximas etapas, nesta ordem (`ARCHITECTURE.md`, seção
16): `local_id` e features, notebooks de EDA, modelagem com MLflow, DAGs do Airflow,
simulador embarcado e ingestor MQTT, API FastAPI e dashboard Streamlit.

## Como executar

Pré-requisito: Docker com Compose v2 (no Windows, Docker Desktop com WSL2). Não é preciso
Python, venv nem nenhuma biblioteca no host.

**1. Configure o `.env`** (uma vez):

```bash
cp .env.example .env              # PowerShell: Copy-Item .env.example .env
```

Troque `POSTGRES_PASSWORD`, `MQTT_PASSWORD` e `JUPYTER_TOKEN`. A senha do Postgres entra na
URI do MLflow, então evite `@ : / ? # %` nela. No Linux, ponha em `AIRFLOW_UID` a saída de
`id -u`, para os arquivos gravados em `data/` e `notebooks/` ficarem com o seu usuário. No
Windows e no macOS, deixe `50000`.

**2. Rode:**

```bash
docker compose up                                              # sobe postgres, mosquitto e mlflow (primeiro plano; -d para segundo plano)
docker compose --profile dev up jupyter                        # notebooks em http://localhost:8888 (token = JUPYTER_TOKEN)
docker compose run --rm tooling python -m src.ingestao.fetch_datasets   # baixa os 10 CSVs
docker compose run --rm tooling python -m src.preparo.clean_sinistros   # gera o Parquet limpo
docker compose run --rm tooling pytest                         # roda os testes
docker compose down -v                                         # derruba tudo e apaga os volumes
```

Na primeira vez, o `docker compose up` e o `docker compose run` montam as imagens a partir do
`requirements.txt`, o que leva alguns minutos; as imagens Python compartilham a camada das
dependências, então ela é instalada uma vez só. Depois de mudar o `requirements.txt`, rode
`docker compose build`. Mudanças em `src/`, `tests/` e `notebooks/` não exigem rebuild, porque
entram nos containers por bind mount.

O banco `mlflow` é criado só quando o volume `pgdata` nasce. Se você já tinha subido o
Postgres antes desta versão, rode `docker compose down -v` uma vez.

O `fetch_datasets` aceita `--force` para baixar de novo mesmo o que não mudou.

### Serviços e portas

| Serviço | Imagem | Porta no host | Papel |
|---|---|---|---|
| `postgres` | `postgres:16` | `5433` (`POSTGRES_PORT`) | bancos `viario` (dados da solução) e `mlflow`; volume nomeado `pgdata` |
| `mosquitto` | `eclipse-mosquitto:2` | `1883` (`MQTT_PORT`) | broker MQTT; login com `MQTT_USER`/`MQTT_PASSWORD`, sem acesso anônimo |
| `mlflow` | `docker/mlflow/Dockerfile` | `5000` (`MLFLOW_PORT`) | tracking server e Model Registry; artefatos no volume nomeado `mlflow_artifacts` |
| `jupyter` | `docker/jupyter/Dockerfile` | `8888` (`JUPYTER_PORT`) | JupyterLab para `notebooks/` (profile `dev`, não sobe no `up`) |
| `tooling` | `docker/python/Dockerfile` | nenhuma | ingestão, preparo e testes via `docker compose run --rm` (profile `tooling`, não sobe no `up`) |

Dentro da rede do compose, os serviços se acham pelo nome: `postgres:5432`, `mosquitto:1883`,
`http://mlflow:5000`. No macOS, a porta 5000 costuma estar ocupada pelo AirPlay: troque
`MLFLOW_PORT` para `5001`.

### O que cada etapa gera

| Caminho | Conteúdo | Versionado |
|---|---|---|
| `data/raw/cttu/acidentes-de-transito-com-e-sem-vitimas/*.csv` | os 10 CSVs anuais, como vieram do portal | não |
| `data/manifest.jsonl` | proveniência de cada download | sim |
| `data/processed/sinistros/sinistros_2015_2024.parquet` | uma linha por chamado de sinistro, esquema unificado | não |
| `data/processed/sinistros/colunas_por_ano.json` | colunas encontradas em cada CSV anual | não |
| `data/processed/sinistros/README.md` | ressalvas da fonte, contagens por ano e duplicados removidos | não |

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
├── docker-compose.yml       # postgres, mosquitto, mlflow, jupyter (dev) e tooling
├── .env.example             # variáveis do compose (copie para .env)
├── requirements.txt         # dependências Python (ARCHITECTURE.md, seção 14)
├── docker/
│   ├── python/              # Dockerfile do tooling
│   ├── mlflow/              # Dockerfile do tracking server
│   ├── jupyter/             # Dockerfile do JupyterLab
│   ├── mosquitto/           # mosquitto.conf (sem acesso anônimo)
│   └── postgres/init/       # cria o banco do MLflow na primeira subida
├── notebooks/               # notebooks de EDA e features (etapa 4)
├── src/
│   ├── ingestao/            # ckan_client, manifest, fetch_datasets
│   └── preparo/             # clean_sinistros (normalizar_schema + limpeza)
├── tests/                   # pytest
├── embedded/esp32/          # README do módulo ESP32 (payload MQTT com local_id)
├── data/                    # raw/ e processed/ fora do git; manifest.jsonl versionado
└── legado/mvp-geocodificado/ # MVP anterior (Nominatim + PostGIS), fora da solução atual
```

## Legado e histórico

O MVP anterior, baseado em geocodificação (Nominatim + PostGIS e contrato de trechos lat/lon),
foi movido sem apagar para `legado/mvp-geocodificado/`. O README de lá explica o porquê.

O material do Projeto 6 que dividia este repositório (`docs/`, `pesquisa-qualitativa/`) e as
configurações de agentes de IA (`.github/`, `.agents`, `.codex`, `.cursor`, `.goose`, `.grok`,
`.kimi-code`, `.omp`) foram removidos e seguem só no histórico do git. `CLAUDE.md` e `.claude/`
são configuração local de quem usa o Claude Code e estão no `.gitignore`.

## Origem dos dados

Portal de Dados Abertos do Recife (CKAN), dataset
[`acidentes-de-transito-com-e-sem-vitimas`](https://dados.recife.pe.gov.br/dataset/acidentes-de-transito-com-e-sem-vitimas),
licença ODbL. São **chamados** registrados pela CTTU, que podem divergir dos números dos
relatórios anuais oficiais. 2015 só tem dados a partir de junho.
