# 07 — Backlog de tarefas para o Claude Code

Ordem sugerida. Cada tarefa pressupõe que as anteriores foram concluídas, mas pode ser
reordenada se fizer mais sentido durante a implementação.

## T1 — Estrutura do projeto

Criar `scripts/` com um layout simples (ex.: `scripts/ckan_client.py`,
`scripts/fetch_datasets.py`, `scripts/fetch_pdfs.py`, `scripts/manifest.py`). Adicionar
`requirements.txt` (requests, pandas, pyarrow, e o que mais for necessário) e um `.gitignore`
cobrindo `data/raw/` e `data/processed/` (dados baixados não devem ir pro controle de
versão).

## T2 — Cliente CKAN reutilizável

Função/classe que encapsula `package_search` e `package_show` contra
`dados.recife.pe.gov.br/api/3/action/`, com tratamento de erro de rede e rate limiting
básico (a API não documenta limites, mas evitar rajadas de requisições).

## T3 — Downloader de datasets essenciais

Implementar o fluxo de `05-arquitetura-extracao.md` para os datasets marcados como
**essencial** e **complementar** no catálogo (seções A, C e E — sinistros, infrações,
equipamentos, semáforos, SAMU). Perguntar ao usuário antes de expandir para velocidade das
vias (seção B, volume grande de recursos) ou para os datasets de baixa prioridade (seção D).

## T4 — Downloader + extrator de PDFs institucionais

Baixar o PDF do PSVR (URL direta) e os 5 PDFs dos Relatórios Anuais (via Google Drive,
resolvendo os IDs listados no catálogo). Extrair texto e, quando possível, tabelas (metas do
PSVR por eixo/iniciativa/ação; séries anuais dos Relatórios). Confirmar manualmente a que
ano corresponde cada um dos 5 relatórios (o catálogo já avisa que os 2 últimos não foram
identificados com certeza pelo nome do arquivo).

## T5 — Carregar os dicionários de dados oficiais

Vários datasets trazem um "Dicionário de Dados" próprio (JSON ou PDF) com os valores
categóricos válidos (ex.: tipos de infração, subtipos do SAMU). Escrever um parser que
carregue esses dicionários e os use para validar os valores encontrados nos CSVs
correspondentes — sinalizar quando um valor no CSV não aparece no dicionário oficial.

## T6 — Normalização e schema

Para cada dataset baixado, gerar uma versão em `data/processed/` com tipos consistentes
(datas como `datetime`, números como `float`/`int` em vez de string com vírgula decimal) e
um pequeno `README` ao lado documentando as colunas (baseado em `04-esquemas-datasets.md`,
mas atualizado com o que for confirmado durante a implementação).

## T7 — Relatório de qualidade de dados

Script que gera um resumo por dataset: período coberto, contagem de linhas por ano,
percentual de campos vazios por coluna, e um alerta específico para os casos já conhecidos
(encoding dos Equipamentos, cobertura parcial de 2015, filtro de município no SAMU).

## T8 — Exploração de correspondência sinistros × SAMU

Só depois de T3–T7 estarem estáveis: um notebook/script exploratório que tenta aproximar
registros de sinistro e atendimento SAMU por data + janela de horário + bairro, reportando
quantos pares plausíveis foram encontrados e a taxa de ambiguidade (mais de um candidato por
sinistro). Tratar como exploração, não como pipeline de produção — o objetivo é informar se
vale a pena investir mais nessa direção para as próximas etapas do projeto.

## Não fazer ainda

Ideação de solução, prototipagem de produto ou definição de trilha técnica — fora de escopo
enquanto o projeto está na fase de desk research / levantamento de dados (ver
`01-visao-geral.md`).
