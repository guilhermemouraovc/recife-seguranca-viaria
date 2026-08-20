# Segurança viária no Recife — dados para Projeto 6

Ambiente de contexto e código para a etapa de **extração de dados** do projeto de segurança
viária no Recife (Projeto 6, CESAR School). A desk research já definiu o tema e o problema
preliminar:

> Como os dados atualmente disponíveis sobre os sinistros de trânsito no Recife podem ser
> melhor compreendidos e utilizados para identificar padrões e acompanhar a segurança viária?

Este repositório é **agentificado**: abra com Claude Code (ou outro agente compatível) e ele
já entende o contexto do projeto, as regras que precisam ser seguidas e as skills prontas
pra usar — sem precisar redescobrir nada do zero a cada conversa.

## Como usar

1. Abra o repositório com Claude Code. Ele lê `CLAUDE.md` automaticamente — as regras de lá
   valem sempre, independente do que você pedir.
2. Ambiente Python já está em `.venv/` (requirements em `requirements.txt`: requests,
   pandas, pyarrow, pdfplumber). Use `.venv/bin/python`, não o Python do sistema.
3. Pra rodar a pipeline principal:
   - `scripts/fetch_datasets.py` — baixa os datasets do Portal de Dados Abertos (CKAN).
   - `scripts/fetch_pdfs.py` + `scripts/extract_pdfs.py` — baixa e extrai os PDFs
     institucionais (PSVR + Relatórios Anuais).
   - `scripts/build_dashboard_data.py` / `web/` — dashboard exploratório dos dados já
     processados.
4. Se está usando outro agente/IDE sem suporte a skill, comece por `docs/01-visao-geral.md`
   e siga a ordem numerada da pasta `docs/`.

## Pesquisa qualitativa (semana 3–4)

O desk research foi aprovado; a etapa atual é entrevistar profissionais da Secretaria de
Trânsito/CTTU (ver `docs/00-contexto-cesar.md`). Isso roda num harness separado, com contrato
próprio (não confundir com as regras da extração de dados):

- `pesquisa-qualitativa/CLAUDE.md` — o que vale como evidência ali (claim ledger contestável).
- `pesquisa-qualitativa/README.md` — fluxo completo.
- Comandos `/pesquisar`, `/consolidar`, `/contestar`, `/fundamentar` em `.claude/commands/`.

## Skills disponíveis

- **`extract-pdf-adhoc`** — extração de PDF avulso, fora do fluxo dos PDFs institucionais.
  Uso: peça pro agente "extrair esse PDF: `<caminho>`" (ou solte o arquivo você mesmo em
  `data/adhoc/raw/` e peça pra rodar). A extração é 100% `pdfplumber` — texto e tabela nativos
  do PDF, **sem IA/OCR** — o agente só cria a pasta, roda o script e reporta o resultado.
  Saída em `data/adhoc/processed/` (git-ignorado, acumula entre usos). PDF escaneado/sem
  camada de texto real gera aviso explícito, não é "resolvido" silenciosamente. Detalhes em
  `.claude/skills/extract-pdf-adhoc/SKILL.md`.

Se seu grupo criar novas skills de projeto, coloque em `.claude/skills/<nome>/SKILL.md` — é
compartilhado com todo mundo que puxar o repo, não precisa reconfigurar nada.

## Regras que valem pra qualquer pesquisa/contribuição neste repo

Estão detalhadas em `CLAUDE.md`, mas as que mais pegam gente de surpresa:

- **Dados são públicos, mas o SAMU é sensível** (sexo/idade/bairro por chamado) — nunca usar
  pra tentar reidentificar alguém, mesmo agregando.
- **URLs de download do CKAN expiram em ~1h** — nunca hardcodar uma URL assinada num
  manifesto ou doc de longo prazo; sempre resolver na hora via API.
- **Limitações conhecidas não se "corrigem" — se sinalizam.** Encoding corrompido num
  dataset, cobertura parcial de 2015, "chamados" ≠ números dos relatórios oficiais, 2025
  como preliminar: tudo isso é ressalva documentada (`docs/06`), não bug a esconder.
- **Escopo essencial vs. complementar ainda está em aberto** — antes de expandir a extração
  pra mais datasets (ver prioridades em `docs/02`), perguntar.
- **Pesquisa externa (fora dos datasets) sempre com fonte citada e datada** — ver
  `docs/08-fundamentacao-e-oportunidades.md` como exemplo de formato: argumento + link pra
  cada afirmação, e deixado explícito o que é achado vs. o que ainda é hipótese pra ideação.
- **Ideação de solução ainda não começou** (só na semana 5, ver `docs/00-contexto-cesar.md`)
  — pesquisa e argumentação valem, mas evite já tratar um caminho de solução como decidido.

## Estrutura

```
.
├── CLAUDE.md                              # instruções para o agente (lidas automaticamente)
├── README.md                              # este arquivo
├── .claude/skills/                        # skills de projeto (ex.: extract-pdf-adhoc)
├── docs/
│   ├── 00-contexto-cesar.md               # prazos e trilha técnica do curso
│   ├── 01-visao-geral.md
│   ├── 02-catalogo-de-dados.md            # todo dataset encontrado, com URLs e API
│   ├── 03-ontologia.md                    # entidades e como (não) se relacionam
│   ├── 04-esquemas-datasets.md            # colunas reais, já inspecionadas
│   ├── 05-arquitetura-extracao.md         # como estruturar o pipeline
│   ├── 06-limitacoes-metodologicas.md     # ressalvas que não podem ser perdidas
│   ├── 07-backlog-tarefas.md              # tarefas concretas, em ordem
│   └── 08-fundamentacao-e-oportunidades.md # argumento do tema + pesquisa externa citada
├── scripts/
│   ├── ckan_client.py / fetch_datasets.py  # pipeline dos datasets CKAN
│   ├── fetch_pdfs.py / extract_pdfs.py     # pipeline dos PDFs institucionais
│   ├── extract_adhoc.py                    # extração ad-hoc (skill extract-pdf-adhoc)
│   ├── manifest.py                         # provenance/idempotência dos downloads
│   └── build_dashboard_data.py             # gera dados pro dashboard em web/
├── pesquisa-qualitativa/                   # harness da pesquisa com a Secretaria de Trânsito
│   ├── CLAUDE.md / AGENTS.md               # contrato e papéis (scout/synthesizer/adversary/architect)
│   ├── research/                           # 00-questions.md, claims.md, sources/, findings/
│   ├── evals/ledger.eval.md                # portão de qualidade antes de gerar artefato
│   └── artifacts/                          # roteiro de entrevista + mapeamento de respondentes
├── data/
│   ├── raw/       # (git-ignorado) downloads brutos
│   ├── processed/ # (git-ignorado) dados tratados
│   └── adhoc/     # (git-ignorado) entrada/saída da extração ad-hoc de PDF
└── web/           # dashboard estático (index.html + data.json)
```

## Origem da informação

Tudo em `docs/` foi levantado consultando diretamente a API pública do Portal de Dados
Abertos do Recife (CKAN, `dados.recife.pe.gov.br/api/3/action/...`) e o site da CTTU
(`cttu.recife.pe.gov.br`) em 14/08/2026, mais pesquisa externa citada (14 e 18/08/2026,
`docs/08`). Datasets são vivos — números de recursos, anos disponíveis e URLs assinadas
mudam; trate o catálogo como um mapa de partida, não como verdade congelada, e sempre
re-consulte a API antes de baixar (ver `docs/05`).
