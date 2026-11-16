# ARQUITETURA — Solução de ML para Segurança Viária no Recife

**Versão 2** — revisada após o diagnóstico do repositório de 16/11.
Substitui integralmente a versão 1. Onde esta versão contraria a anterior, vale esta.
Atualizada em 16/11: o material do Projeto 6 e as configurações de agentes saíram do repositório (seção 15).

Documento de referência para a implementação. Leia tudo antes de escrever qualquer arquivo.
Siga as decisões aqui sem substituí-las por alternativas "melhores".

---

## 1. Contexto e objetivo

Projeto da disciplina de **Aprendizado de Máquina** (CESAR School, 2026.6, 2ª unidade).
A solução prevê **quais locais do Recife têm maior risco de acidente com vítima no próximo trimestre**, e entrega esse ranking para a CTTU por API e dashboard.

Pesos da nota: Análise de Dados 15%, Modelagem e Validação 30%, MLOps 25%, Comunicação 20%.
Toda decisão técnica deve servir a um desses blocos.

O material do **Projeto 6** que dividia este repositório (`docs/`, `pesquisa-qualitativa/`) e as configurações de agentes de IA foram removidos; seguem só no histórico do git — ver seção 15.

---

## 2. Dados

### 2.1 Fonte

Portal de Dados Abertos do Recife, dataset `acidentes-de-transito-com-e-sem-vitimas`, arquivos anuais de 2015 a 2024, descobertos via CKAN:

```
https://dados.recife.pe.gov.br/api/3/action/package_show?id=acidentes-de-transito-com-e-sem-vitimas
```

Reaproveite `ckan_client.py`, `manifest.py` e `fetch_datasets.py` da master. A ingestão fica **só** nesse slug e só em CSV.

### 2.2 Esquema real

O dicionário do portal não bate com os CSVs. O que vale é o que foi verificado nos arquivos:

| Fato verificado | Consequência |
|---|---|
| A coluna `timestamp` **não existe**. O nome real é `data`, e em 2018–2019 é `DATA` | `normalizar_schema` mapeia `data`/`DATA` → `data` |
| `endereco_cruzamento` só existe em **2016–2019** | Não pode entrar na chave do local. Ver 3.1 |
| `acidente_verificado` só existe de **2018** em diante | **Não filtrar por ela.** Vira feature categórica com `DESCONHECIDO` antes de 2018 |
| `hora` está vazia em **todo o CSV de 2022** | Não pode entrar na chave do local. Ver 3.1 |
| A proporção de acidentes com vítima salta de ~19% (2015–2019) para 43% (2020) e 77–88% (2021–2024) | Quebra de série no alvo. Ver 3.2 |

**Primeira tarefa antes de qualquer feature:** verificar se a hora de 2022 é recuperável — se a coluna `data` de 2022 carrega componente de horário, ou se existe outra coluna com o horário sob outro nome. Reportar o resultado antes de seguir.

Demais colunas, agrupadas:

| Grupo | Colunas |
|---|---|
| Data e hora | `data`, `hora` |
| Natureza | `natureza_acidente`, `situacao`, `tipo`, `descricao`, `acidente_verificado` |
| Local | `bairro`, `endereco`, `numero`, `detalhe_endereco_acidente`, `complemento`, `endereco_cruzamento`, `numero_cruzamento`, `referencia_cruzamento`, `bairro_cruzamento`, `num_semaforo`, `sentido_via` |
| Envolvidos | `auto`, `moto`, `ciclom`, `ciclista`, `pedestre`, `onibus`, `caminhao`, `viatura`, `outros`, `vitimas`, `vitimasfatais` |
| Via e condições | `tempo_clima`, `situacao_semaforo`, `sinalizacao`, `condicao_via`, `conservacao_via`, `ponto_controle`, `situacao_placa`, `velocidade_max_via`, `mao_direcao`, `divisao_via1`, `divisao_via2`, `divisao_via3` |

`normalizar_schema` é etapa própria: minúsculas, sem acento, sem espaço, coluna ausente vira nulo, e **log do conjunto de colunas encontrado por ano**, salvo como artefato.

### 2.3 Não existe geocodificação

Não há latitude nem longitude no dado. As features de via — velocidade máxima, semáforo, sinalização, conservação — já são colunas do CSV. Sem malha viária, sem banco espacial, sem Nominatim.

---

## 3. Modelagem do problema

### 3.1 Unidade de análise

```
local_id × trimestre
```

**Mudou em relação à versão 1:** a faixa horária saiu da chave. `hora` está vazia em 2022, que é ano de treino, e o cruzamento só existe em 2016–2019. Nenhum dos dois é estável ao longo da série, então nenhum dos dois entra na identidade do local. Ambos viram **feature**, onde existem.

**`local_id`**, derivado só de texto e estável nos 10 anos:

1. Normalize `bairro` e `endereco`: maiúsculas, sem acento (`unidecode`), sem pontuação, espaços colapsados, removendo os prefixos `RUA`, `R.`, `AV`, `AVENIDA`, `TRAVESSA`, `TV`, `ESTRADA`, `ESTR`, `PRACA`, `PCA`.
2. `local_id = sha1(bairro_norm + "|" + logradouro_norm)[:12]`.
3. Tabela `dim_local` com a chave, o bairro e o logradouro legíveis, para a API e o dashboard mostrarem o nome e não o hash.
4. Registre quantos `local_id` distintos saíram e a distribuição de acidentes por local.

**`trimestre`**: derivado de `data`, no formato `2024Q1`.

**Grade**: só locais com **≥ 3 acidentes na série inteira**. Locais com um ou dois registros são ruído e inflam a classe negativa. Reporte na EDA quantos locais sobram e qual o balanceamento resultante; o limiar pode mudar com evidência.

### 3.2 Alvo e recorte temporal

```
y = 1  se o local teve >= 1 acidente com vítima no trimestre SEGUINTE
y = 0  caso contrário
```

Acidente com vítima = `vitimas > 0` ou `vitimasfatais > 0`.

**Quebra de série.** Os registros "sem vítima" praticamente desaparecem a partir de 2020, o que muda o significado do alvo. Tratamento:

- **Linhas de treino, validação e teste: só de 2020Q1 em diante.** 2015–2019 entra **apenas** como histórico das features.
- Features de histórico em **duas formas**: contagem absoluta e **participação relativa** (a fração dos acidentes da cidade naquele trimestre que caiu naquele local). A relativa é imune à mudança de patamar do registro.
- Incluir `ano` como feature e um booleano `periodo_pandemia` para 2020–2021.
- A EDA precisa trazer o gráfico da proporção por ano e justificar o corte. Se 2020 se mostrar ainda em transição, mova o corte para 2021Q1 e registre a decisão.

Janelas resultantes na seção 4.

### 3.3 Features

Todas calculadas **apenas com dados até o trimestre da linha**. O alvo é o trimestre seguinte. Feature que use o futuro é vazamento e invalida o projeto — tem teste próprio para isso.

**Histórico no local** (cada uma em contagem absoluta e em participação relativa):
- acidentes no trimestre atual, nos últimos 2 e nos últimos 4 trimestres
- acidentes com vítima nos mesmos recortes
- acidentes com vítima fatal nos últimos 4 trimestres
- trimestres consecutivos com pelo menos um acidente
- trimestres desde o último acidente com vítima

**Perfil horário** (das linhas com `hora` preenchida; nulo com flag `hora_indisponivel` onde não houver):
- fração histórica de acidentes do local em madrugada (0–5), manhã (6–11), tarde (12–17) e noite (18–23)
- fração em fim de semana

**Cruzamento** (de `endereco_cruzamento` onde existe, 2016–2019):
- `tem_cruzamento_registrado` booleano
- nº de vias transversais distintas já registradas no local

**Envolvidos** (média histórica no local): `auto`, `moto`, `ciclom`, `ciclista`, `pedestre`, `onibus`, `caminhao`.

**Via** (moda ou último valor conhecido no local): `velocidade_max_via`, `sinalizacao`, `condicao_via`, `conservacao_via`, `situacao_semaforo`, `mao_direcao`, `sentido_via`, `ponto_controle`, `situacao_placa`, `divisao_via1`, `tem_semaforo` (de `num_semaforo` não nulo), `acidente_verificado`.

**Contexto**: `tempo_clima` e `natureza_acidente` mais frequentes no local.

**Bairro**: nº de acidentes do bairro no trimestre anterior; o bairro como categórica.

**Temporal**: número do trimestre no ano (1 a 4), `ano`, `periodo_pandemia`.

**Telemetria** (quando houver dados do ESP32, agregados por local × trimestre): velocidade média, velocidade máxima, nº de passagens, nº de frenagens bruscas. Nulo nos períodos sem telemetria.

### 3.4 Tratamento

- **Nulos**: numéricos por mediana do treino; categóricos por `DESCONHECIDO`. Justificar na EDA.
- **Encoding**: `OneHotEncoder(handle_unknown='ignore')` nas categóricas de baixa cardinalidade; `bairro` com one-hot nos 20 mais frequentes e `OUTROS` no resto.
- **Normalização**: `StandardScaler` nas numéricas — obrigatório para KNN, MLP e Regressão Logística.
- Tudo num `Pipeline` + `ColumnTransformer` do scikit-learn, **ajustado só no treino**. Tem teste para isso.
- **Desbalanceamento**: `class_weight='balanced'` onde o modelo suportar, e justificar o limiar de decisão. Não usar SMOTE.
- Duplicados: remover, mantendo registro de quantos saíram. As flags `DUPLICIDADE` e `CANCELADA` continuam como coluna.

---

## 4. Validação

| Estratégia | Como aplicar |
|---|---|
| **Holdout temporal** | Treino: 2020Q1 a 2022Q4. Validação: 2023. Teste: 2024. É a divisão principal, porque o problema é de previsão no tempo |
| **k-fold estratificado** | `StratifiedKFold(n_splits=5)` dentro do treino, para comparar modelos e rodar o Optuna |
| **Leave-One-Out** | Não se aplica: a base tem dezenas de milhares de linhas e LOO seria inviável. **Registrar essa justificativa no notebook e no relatório** — a especificação pede "quando aplicável" |
| **Overfitting / underfitting** | `learning_curve` e comparação treino × validação por modelo |
| **Estabilidade** | Desvio padrão das métricas entre os folds, reportado junto da média |

**Otimização**: `RandomizedSearchCV` como referência e **Optuna** como estratégia principal, nos 2 melhores modelos. Documentar espaço de busca, nº de trials e resultado.

---

## 5. Métricas (definidas antes do treino)

| Métrica | Papel |
|---|---|
| **PR-AUC** (average precision) | Métrica principal de seleção |
| **Recall@50** e **Recall@100** | Dos 50 e 100 locais mais arriscados, quantos de fato tiveram acidente com vítima. É a métrica que a CTTU entende |
| ROC-AUC | Comparação secundária |
| F1, precisão, recall | No limiar escolhido |
| Matriz de confusão | Obrigatória |

**Registrar explicitamente que acurácia não é usada, e por quê.**

Visualizações obrigatórias: matriz de confusão por modelo, curva precisão-recall, curva ROC, barras comparando as métricas, curva de aprendizado.

---

## 6. Modelos

**Baseline**: `LogisticRegression(class_weight='balanced', max_iter=1000)` — interpretável, dá coeficientes, serve de piso.

**Comparação**, os cinco do scikit-learn: `KNeighborsClassifier`, `DecisionTreeClassifier`, `RandomForestClassifier`, `AdaBoostClassifier`, `MLPClassifier`.

**Interpretabilidade**: `permutation_importance` sobre o melhor modelo, com gráfico.

**Não incluir nesta fase**: XGBoost, LightGBM, statsmodels, SHAP, Evidently. Entram depois, em branch separada.

---

## 7. MLflow

Servidor próprio, backend no PostgreSQL, artefatos em volume local.

Três experimentos, com estes nomes exatos:

1. `01_baseline` — só a Regressão Logística
2. `02_comparacao_modelos` — os cinco modelos, um run cada
3. `03_otimizacao_hiperparametros` — um run por trial do Optuna

Em todo run: parâmetros, todas as métricas da seção 5, e como artefatos os gráficos em PNG e o `classification_report` em texto. Modelo salvo com `mlflow.sklearn.log_model`.

Ao fim do experimento 3, registrar o melhor no Model Registry como `risco-viario`, alias `@champion`. A DAG de scoring carrega `models:/risco-viario@champion`.

---

## 8. Aquisição e MQTT

### 8.1 Sistema embarcado

- `embedded/simulador/` — serviço Python que gera passagens de veículo sobre uma lista de locais, publicando velocidade, horário e frenagens. É o que roda no compose e o que será demonstrado.
- `embedded/esp32/` — sketch Arduino com o mesmo payload. Opcional na demonstração. Parte do conteúdo de `firmware/README.md` da master, **trocando o alerta por lat/lon pelo `local_id`**.

### 8.2 Tópicos

| Tópico | Quem publica | Payload |
|---|---|---|
| `viario/telemetria` | ESP32 / simulador | `{"device_id","local_id","timestamp","velocidade_kmh","frenagem_brusca":bool}` |
| `viario/modelo/versao` | DAG de scoring | `{"versao","run_id","gerado_em","n_locais"}` |
| `viario/status/<servico>` | cada serviço | `{"servico","status","timestamp"}` |

### 8.3 Persistência

Serviço `ingestor` com `paho-mqtt`, assinando `viario/telemetria`, gravando na tabela `telemetria` do PostgreSQL, com reconexão automática.

---

## 9. Pipeline — Apache Airflow

Exatamente **três DAGs**, `LocalExecutor`, metadados no mesmo PostgreSQL.

### `dag_ingestao_preparo` — `@monthly`
1. `baixar_csvs` — CKAN, `data/raw/`, SHA-256 via manifesto
2. `normalizar_schema` — unifica cabeçalhos entre anos, salva o log de colunas por ano
3. `limpar` — tipos, nulos, duplicados. **Sem filtrar `acidente_verificado`**
4. `construir_local_id` — seção 3.1, grava `dim_local`
5. `montar_features` — seção 3.3, grava `features` no Postgres e Parquet em `data/processed/`
6. `validar` — asserts com pytest: nº de linhas, nulos nas colunas obrigatórias, intervalo das datas, **e o teste de não-vazamento**. Falha a DAG se não passar

### `dag_treino` — `@monthly` e manual
`carregar_features` → `split_temporal` → `treinar_baseline` → `comparar_modelos` → `otimizar` → `registrar_campeao`

### `dag_scoring` — `@weekly`
`carregar_modelo` → `gerar_inferencias` → `gravar_scores` → `publicar_aviso` (MQTT)

Não criar uma quarta DAG. A telemetria é serviço contínuo.

---

## 10. API — FastAPI

| Rota | Retorno |
|---|---|
| `GET /health` | status da API, do banco e do MLflow |
| `GET /locais` | ranking por score. Filtros: `bairro`, `limit` |
| `GET /locais/{local_id}` | detalhe: rótulo, histórico, score, features principais |
| `POST /score` | inferência sob demanda |
| `GET /metrics` | métricas do modelo em produção, do MLflow |
| `GET /modelo` | versão, `run_id` e data de treino do modelo carregado |

Entrada e saída com Pydantic. O OpenAPI em `/docs` é parte da entrega.

---

## 11. Dashboard — Streamlit

Em `app/`, consumindo a API e o MQTT. Cinco abas:

1. **Visão geral** — total de acidentes, locais monitorados, nº em risco alto, última atualização, mais indicadores do Projeto 6
2. **Locais prioritários** — tabela por score, filtro por bairro, detalhe do local
3. **Métricas do modelo** — PR-AUC, recall@k, matriz de confusão, curvas, comparação entre modelos, lidas do MLflow
4. **Telemetria** — dados do MQTT em tempo real: velocidade média por local, passagens, frenagens
5. **Saúde da solução** — status de cada serviço via `/health` e `viario/status/#`, última execução de cada DAG, versão do modelo em uso

---

## 12. Conteinerização — tudo roda em Docker

**Nenhuma parte do projeto depende de Python, venv ou biblioteca instalada no host.** Se algo só roda fora do container, está errado. Isso vale para a execução, para os testes e para os notebooks.

`docker compose up` sobe a solução inteira com **um comando**.

| Serviço | Imagem | Papel |
|---|---|---|
| `postgres` | `postgres:16` | dados + metadados do Airflow + backend do MLflow |
| `mosquitto` | `eclipse-mosquitto:2` | broker MQTT |
| `mlflow` | build próprio | tracking server |
| `airflow-init` | `apache/airflow:2.9` | migração e usuário inicial |
| `airflow-webserver` | `apache/airflow:2.9` | UI |
| `airflow-scheduler` | `apache/airflow:2.9` | execução das DAGs |
| `api` | build próprio | FastAPI |
| `dashboard` | build próprio | Streamlit |
| `ingestor` | build próprio | subscriber MQTT |
| `simulador` | build próprio | sistema embarcado simulado |
| `jupyter` | build próprio, profile `dev` | execução dos notebooks |

Requisitos:
- `healthcheck` em postgres, mosquitto, mlflow e api
- `depends_on` com `condition: service_healthy`
- volumes nomeados para dados do Postgres e artefatos do MLflow
- credenciais e portas em `.env`, com `.env.example` versionado
- sem portas conflitantes; cada uma documentada no README

Comandos que o README tem que trazer, e que precisam funcionar:

```
docker compose up                              # sobe a solução
docker compose --profile dev up jupyter        # notebooks
docker compose run --rm api pytest             # testes
docker compose down -v                         # derruba e limpa
```

---

## 13. Estrutura do repositório

Pastas da trilha de AM:

```
├── data/raw/ data/processed/   # gitignored
├── notebooks/
│   ├── 01_eda_bootstrap.ipynb
│   └── 02_preparacao_features.ipynb
├── src/
│   ├── ingestao/   preparo/   modelagem/   comum/
├── embedded/simulador/   embedded/esp32/
├── dags/
├── api/
├── app/
├── tests/
├── reports/                    # relatório em template SBC
├── docker/                     # Dockerfiles por serviço
├── legado/mvp-geocodificado/   # MVP anterior, fora da solução (15.2)
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

`docs/`, `pesquisa-qualitativa/`, `.github/` e as pastas de configuração de agentes foram removidos (seção 15.1).

### Notebooks

`01_eda_bootstrap.ipynb`, nesta ordem: carga, estatísticas descritivas, nulos e duplicados, **o log de colunas por ano**, **o gráfico da proporção de acidentes com vítima por ano**, distribuição do alvo, e **no mínimo 5 visualizações, cada uma com um parágrafo de interpretação abaixo**. As decisões de tratamento da 3.4 e o corte temporal da 3.2 são justificados aqui, não só no código. Os achados do diagnóstico — `data` em vez de `timestamp`, cruzamento só em 2016–2019, `hora` vazia em 2022, `acidente_verificado` só de 2018 — entram como ressalvas documentadas.

### README

Obrigatório: nome e sobrenome de cada integrante com `@usuario` do GitHub, nome criativo da solução, instruções detalhadas de execução, descrição breve e link do Google Sites. **Esses dados ainda não existem no repositório — deixe placeholders marcados com `TODO:` e liste-os no fim da entrega.**

---

## 14. Dependências

```
pandas
pyarrow
numpy
scikit-learn
optuna
mlflow
apache-airflow
fastapi
uvicorn
pydantic
httpx
streamlit
plotly
paho-mqtt
psycopg2-binary
sqlalchemy
python-dotenv
requests
unidecode
pytest
jupyterlab
```

`httpx` entra porque o `TestClient` do FastAPI exige. Nada além desta lista sem justificativa.

---

## 15. O que sai, o que fica e o que nunca entra

### 15.1 Projeto 6 e pastas de agentes: removidos

`docs/`, `pesquisa-qualitativa/`, `.github/` e as pastas de configuração de agentes (`.agents`, `.codex`, `.cursor`, `.goose`, `.grok`, `.kimi-code`, `.omp`) foram apagados do repositório em 16/11. Seguem recuperáveis pelo histórico do git. As pastas de agentes, `.claude/` e `CLAUDE.md` estão no `.gitignore`; `.github/` não, para não bloquear um CI futuro.

### 15.2 Mover, não deletar

O MVP geocodificado contraria esta arquitetura. **Mova para `legado/mvp-geocodificado/`** com um `README.md` explicando o porquê e apontando para este documento:

`geocode_sinistros.py`, `data/geocode/`, `tests/test_geocode_sinistros.py`, `sql/01–04`, `load_postgis.sh`, `sql/locais_validacao.csv`, `validar_trechos.py`, `data/contrato/`, a `api/` antiga, `tests/test_api.py`, `painel/`, `web/`, `build_dashboard_data.py`, `fetch_pdfs.py`, `extract_pdfs.py`, `extract_adhoc.py`, `ontologia_grafo.py`.

Nenhum desses arquivos pode ser importado pelo código novo, e nenhum entra no `docker-compose.yml` nem no `requirements.txt`.

O contrato de trechos lat/lon (`docs/09`) e a documentação da base geocodificada (`docs/11`) saíram com `docs/` (15.1).

### 15.3 CLAUDE.md e .claude/

`CLAUDE.md` e `.claude/` são **locais**: ficam na raiz de quem usa o Claude Code, fora do git (`.gitignore`). O `CLAUDE.md` local diz só que, para tudo sob `src/`, `dags/`, `api/`, `app/`, `embedded/`, `tests/` e `notebooks/`, a autoridade é o `ARCHITECTURE.md`.

### 15.4 Nunca entram

- **Geoprocessamento**: OSMnx, GeoPandas, Shapely, PostGIS, Nominatim, PySAL, h3-py, Splink
- **Armazenamento de objetos**: S3, MinIO, boto3
- **Nuvem**: EC2, ECR, IAM, CloudWatch, RDS, IoT Core, SageMaker
- **Modelos extras nesta fase**: XGBoost, LightGBM, statsmodels
- **Interpretabilidade extra nesta fase**: SHAP
- **Monitoramento extra nesta fase**: Evidently, PSI caseiro, drift, retreino automático
- **Big data**: Spark, Dask, EMR
- **Validação de schema**: pandera
- **pdfplumber** e qualquer dependência de extração de PDF
- **Mais de três DAGs**

---

## 16. Ordem de implementação

Base: branch `fix/ml-architecture-base`, criada a partir da `master`. Nada vem da `m4-m5-m6` nem das demais.

1. **Mover o legado** (15.2) e ajustar o `CLAUDE.md` (15.3)
2. **Docker**: `docker-compose.yml`, `.env.example`, `docker/`, com postgres, mosquitto e mlflow subindo e healthcheck passando
3. **`src/ingestao` e `src/preparo`**: ckan_client, manifest, fetch_datasets e clean_sinistros movidos e corrigidos; `normalizar_schema`, `local_id`, `dim_local`, `features`, gravação em Postgres e Parquet, teste de não-vazamento
4. **`notebooks/01_eda_bootstrap.ipynb`** e `02_preparacao_features.ipynb`
5. **`src/modelagem`**: pipeline, baseline, os cinco modelos, Optuna, MLflow, Registry
6. **`dags/`**: as três DAGs e os três serviços do Airflow no compose
7. **`embedded/simulador`** e o serviço `ingestor`
8. **`api/`**
9. **`app/`**
10. **`tests/`** e o README

Cada etapa roda de ponta a ponta, dentro do Docker, antes da seguinte. Não gere esqueleto vazio nem `pass` com `TODO`: cada arquivo entregue precisa executar.
