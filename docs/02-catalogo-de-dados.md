# 02 — Catálogo de dados

Levantado em 14/08/2026 via API pública do CKAN do Portal de Dados Abertos do Recife
(`https://dados.recife.pe.gov.br/api/3/action/`) e do site da CTTU
(`https://cttu.recife.pe.gov.br`). Licença padrão do portal: **Open Data Commons Open
Database License (ODbL)**.

Endpoints da API usados para levantar este catálogo (reutilizar no pipeline):

- `package_search?fq=organization:<slug-da-org>&rows=100` — lista os datasets de uma
  organização.
- `package_search?q=<termo>&rows=N` — busca por palavra-chave em todas as organizações.
- `package_show?id=<slug-do-dataset>` — metadados completos + lista de `resources` (cada um
  com `url`, `format`, `name`, `last_modified`).
- `organization_list` — lista todas as organizações publicadoras do portal.

Prioridade sugerida: **essencial** (direto ligado a sinistros/vítimas/exposição ao risco),
**complementar** (contexto útil, correlação possível) ou **baixa** (mobilidade urbana em
geral, pouca relação direta com o problema de pesquisa).

## A. CTTU — sinistros de trânsito (essencial)

| Dataset | Slug CKAN | Cobertura | Recursos | Formato | Observação |
|---|---|---|---|---|---|
| Chamados de Sinistros (Acidentes) de Trânsito com e sem vítimas 2015–2024 | `acidentes-de-transito-com-e-sem-vitimas` | 2015–2024, 1 CSV/ano | 11 (10 CSVs + 1 JSON de metadados) | CSV, JSON | Dataset consolidado principal. Nota oficial do próprio portal: dados de 2015 só a partir de junho; são dados de **chamados**, podem divergir dos Relatórios Anuais (que usam registros estatísticos dos agentes de trânsito). |
| Acidentes de Trânsito com Vítimas 2014 | `acidentes-de-transito-com-vitimas-2014` | 2014 | 13 | CSV | Pré-consolidação; checar se sobrepõe/substitui o dataset acima para esse ano. |
| Acidentes de Trânsito com Vítimas 2015 | `acidentes-de-transito-com-vitimas-2015` | 2015 | 7 | CSV | Idem — comparar com a fatia 2015 do dataset consolidado. |
| Acidentes de Trânsito com Vítimas 2016 | `acidentes-de-transito-c-vitimas-2016` | 2016 | 2 | CSV | Idem. |
| Registro de chamados atendidos pela CTTU | `registro-de-chamados-atendidos-pela-cttu` | não verificado | 3 | — | Pode ser um universo mais amplo que só sinistros (chamados gerais da central). Checar escopo antes de usar. |

Schema real do CSV principal (`acidentes-de-transito-2024.csv`) documentado em
`04-esquemas-datasets.md`.

## B. CTTU — velocidade das vias (complementar — exposição ao risco)

Um dataset por ano, granularidade de 15 minutos por equipamento (lombada eletrônica /
fotossensor), com contagem de veículos por faixa de velocidade.

| Slug CKAN | Ano | Recursos |
|---|---|---|
| `registro-de-velocidade-das-vias` | 2013–2016 (consolidado antigo) | 7 |
| `velocidade-das-vias-quantitativo-por-velocidade-media` | 2018 | 4 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2016` | 2016 | 4 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2017` | 2017 | 4 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2019` | 2019 | 27 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2020` | 2020 | 51 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2021` | 2021 | 27 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2022` | 2022 | 25 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2023` | 2023 | 25 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2024` | 2024 | 17 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2025` | 2025 | 37 |
| `velocidade-das-vias-quantitativo-por-velocidade-media-2026` | 2026 (parcial) | 8 |

Cada dataset separa recursos por tipo de equipamento (Lombadas / Fotossensores) e por mês
(ex.: "Lombadas 2024 - Janeiro..."). O número de recursos varia porque nem todo mês/tipo
está sempre presente. Inclui um resource `Dicionário de Dados - Velocidade das Vias` (JSON)
por dataset — usar para confirmar o schema antes de concatenar anos.

## C. CTTU — infrações e fiscalização (complementar)

| Dataset | Slug CKAN | Recursos | Observação |
|---|---|---|---|
| Registro das Infrações de Trânsito (multas) | `registro-das-infracoes-de-transito` | 22 (1 CSV/ano + dicionário PDF + JSON) | Ligado geograficamente aos equipamentos de fiscalização. |
| Equipamentos de Monitoramento e Fiscalização de Trânsito | `equipamentos-de-monitoramento-e-fiscalizacao-de-transito` | 4 | Lista + geolocalização (lat/long) dos radares/lombadas eletrônicas/fotossensores. **Tem corrupção de encoding na fonte** — ver `06-limitacoes-metodologicas.md`. |
| Localização dos Semáforos | `localizacao-dos-semaforos` | 9 | Semáforos gerais + sub-recursos (equipados p/ ciclistas, iluminação para pedestres, para deficientes visuais). |

## D. CTTU — outros datasets de mobilidade (baixa prioridade / contexto)

`malha-cicloviaria-do-recife`, `paraciclos-do-recife`, `fluxo-de-veiculo-por-hora`,
`amostra-de-fluxo-de-veiculos-a-cada-15-minutos`, `zona-azul-eletronico`,
`urbanismo-tatico`, `faixas-e-corredores-de-onibus`, `malha-viaria-de-trens-do-grande-recife`,
`ciclovias-ciclofaixas-estacoes-de-aluguel-de-bikes-e-rotas`, `efetivo-da-defesa-civil`.
Relevantes só se o grupo decidir explorar infraestrutura cicloviária ou exposição por modal
como parte do problema. Não puxar de cara.

## E. Secretaria de Saúde — SAMU (complementar — desfecho/gravidade)

Um dataset por ano, `servico-de-atendimento-movel-de-urgencia-samu-{ANO}`, para
2011–2026 (16 datasets). Cada um traz um CSV `Solicitações de Atendimento {ANO}` e um
`Dicionário de Dados - Chamados Samu {ANO}` (JSON). Cobre **toda a Região Metropolitana do
Recife**, não só a capital — o campo `municipio` precisa ser filtrado para `RECIFE` quando o
recorte for a cidade. Schema real em `04-esquemas-datasets.md`.

Esse dataset é a fonte mais plausível por trás dos números de "vítimas feridas atendidas
pelo SAMU" citados no PSVR (140 mortes / ~5.930 atendimentos em 2025) — mas **não confirmar
isso sem cruzar os números**; o PSVR pode usar uma extração/relatório interno da própria
Secretaria de Saúde que não é exatamente igual ao dataset aberto.

## F. Documentos institucionais (PDF)

| Documento | URL | Observação |
|---|---|---|
| Programa de Segurança Viária do Recife (PSVR) 2026–2036 | `https://cttu.recife.pe.gov.br/sites/default/files/2026-06/PSVR%20%28REV07%29%20_0.pdf` | PDF direto, sem necessidade de scraping. Publicado em `cttu.recife.pe.gov.br/programa-de-seguranca-viaria-do-recife` (repare no slug: **não** é `/programa-de-seguranca-viaria`, que existe mas é uma página diferente/redundante). |
| Relatórios Anuais de Segurança Viária | página `https://cttu.recife.pe.gov.br/relatorios-anuais-de-seguranca-viaria` | **Não são PDFs hospedados no portal** — a página lista 5 links para Google Drive (`drive.google.com/file/d/<ID>/view`). Pela ordem e imagens ao lado dos links, prováveis anos: 2020, 2021, 2022, e dois anos mais recentes não identificados pelo nome do arquivo (possivelmente 2023 e 2024/2025 — **confirmar abrindo cada um**, não assumir). IDs do Drive coletados: `1eHS78nMNuA773CDHjwewQn4Bkrly_w7p`, `1ckXF6eEmKx8gZZrCHSJ-WF504VX3C2ST`, `16_ADl5iRB9OUPo2ulL_F50Lk1Gc762Ll`, `1idoN6SJARUBZSeU6hnL_3rhFuIo_2L5R`, `1V8bQbyg0flkcG-OMkrn6rSBeqt_Ygkvh`. |

Download direto de um arquivo público do Google Drive por ID (sem OAuth, funciona para
arquivos "qualquer pessoa com o link"):
`https://drive.google.com/uc?export=download&id=<ID>`. Arquivos grandes podem exigir lidar
com a página de confirmação de vírus do Drive (token `confirm=`) — tratar esse caso no
código, não assumir que o `uc?export=download` sempre basta.

## G. Organizações do portal (para expandir a busca depois, se necessário)

`organization_list` retornou 31 organizações. As com maior chance de ter dados correlatos
além das já mapeadas: `secretaria-de-ordem-publica-e-seguranca`,
`secretaria-executiva-de-defesa-civil`, `secretaria-de-planejamento-urbano`, `emprel` (é a
empresa de TI que hospeda os dados da CTTU, não necessariamente publica dataset próprio
relevante). Não explorado a fundo nesta rodada — ver `07-backlog-tarefas.md`.
