# Instruções para o Claude Code neste repositório

Este repositório é o ambiente de trabalho para a etapa de **extração e organização de dados
secundários** do Projeto 6 (curso de graduação, CESAR School) sobre segurança viária no
Recife. A desk research (fase anterior, já entregue) identificou o tema, os principais
achados e o delineamento preliminar do problema. Agora o objetivo é **construir um pipeline
de código que baixe, valide e organize os datasets públicos** listados em `docs/`, para dar
suporte a uma análise de dados mais aprofundada nas próximas etapas do projeto.

Leia estes documentos nesta ordem antes de escrever qualquer código:

1. `docs/01-visao-geral.md` — contexto do projeto e o que esta etapa entrega.
2. `docs/02-catalogo-de-dados.md` — cada fonte de dado, com IDs, URLs e API do portal CKAN.
3. `docs/03-ontologia.md` — como as entidades (sinistro, vítima, veículo, local, equipamento,
   infração, atendimento SAMU) se relacionam entre si — e onde **não** existe chave de
   junção direta entre as bases.
4. `docs/04-esquemas-datasets.md` — colunas reais de cada CSV, já inspecionadas.
5. `docs/05-arquitetura-extracao.md` — como estruturar o pipeline (pastas, manifesto,
   tratamento de URLs assinadas que expiram, PDFs via Google Drive).
6. `docs/06-limitacoes-metodologicas.md` — ressalvas que já são conhecidas e **precisam** ser
   preservadas no código (não esconder, não "corrigir" silenciosamente).
7. `docs/07-backlog-tarefas.md` — lista de tarefas concretas, em ordem sugerida de execução.

## Regras gerais

- Todas as fontes são dados públicos abertos (Portal de Dados Abertos do Recife, licença
  ODbL, e dados do SAMU da Secretaria de Saúde). Não há dados pessoais identificáveis nos
  recursos catalogados — mas o dataset do SAMU traz sexo/idade/bairro por chamado, então
  trate como dado sensível agregável, nunca reidentifique indivíduos.
- As URLs de download dos recursos CKAN são **assinadas e expiram em ~1 hora** (redirect
  302 para `ckan-storage-download.app.emprel.gov.br` com parâmetros `X-Amz-*`). Nunca
  hardcode essas URLs assinadas num manifesto de longo prazo — sempre resolva a URL de
  download na hora, a partir do `package_show` da API do CKAN (ver `docs/02` e `docs/05`).
- Pelo menos um dataset (`equipamentos-de-monitoramento-e-fiscalizacao-de-transito`) tem
  corrupção de encoding **na fonte original** (não é um bug de download) — ver
  `docs/06-limitacoes-metodologicas.md`. Não decida sozinho como "corrigir" isso sem
  documentar a decisão.
- Preserve as ressalvas metodológicas do PSVR/CTTU (dados de 2015 só a partir de junho,
  divergência entre "chamados" e "relatórios anuais", dados de 2025 como preliminares) em
  qualquer artefato de dados gerado (README do dataset processado, docstring, etc.).
- Este projeto tem prazo acadêmico — prefira soluções simples e que funcionam
  (requests + pandas + parquet) a infraestrutura sofisticada.

## Escopo separado: pesquisa qualitativa (semana 3–4)

As regras acima valem só para o pipeline de extração de dados. A partir de agora o projeto
também tem uma frente de **pesquisa qualitativa** (entrevistas com a Secretaria de
Trânsito/CTTU), que roda num contrato próprio em `pesquisa-qualitativa/CLAUDE.md` — não
misture as duas: dado aberto/CKAN segue as regras deste arquivo, fundamentação de pergunta de
entrevista segue as regras de lá.

## O que ainda não foi decidido

O escopo de "todos os ~30 datasets da CTTU + 16 do SAMU" vs. "só os essenciais" (sinistros,
velocidade das vias, equipamentos, semáforos, infrações, SAMU e os 2 PDFs institucionais)
ainda não foi fechado com o usuário. `docs/02-catalogo-de-dados.md` marca cada dataset com
uma prioridade sugerida (essencial / complementar / baixa) — comece pelos essenciais e
pergunte antes de expandir para os complementares.
