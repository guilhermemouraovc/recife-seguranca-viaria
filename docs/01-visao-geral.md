# 01 — Visão geral do projeto

## Contexto

Projeto 6, disciplina de graduação (CESAR School). O grupo escolheu o tema **segurança
viária no Recife**, com foco em como os dados disponíveis sobre sinistros de trânsito podem
ser usados para prevenção e priorização de ações. A fase de desk research (entregue em
14/08/2026) já produziu:

- contextualização do problema (global, Brasil, Nordeste, Recife);
- destaque para a participação das motocicletas nas mortes no trânsito;
- mapeamento das iniciativas já existentes no Recife (PSVR 2026–2036, Ruas Seguras, Manual
  de Desenho de Ruas, Relatórios Anuais de Segurança Viária, Portal de Dados Abertos);
- lacunas identificadas: como as informações são acompanhadas e integradas entre os ciclos
  de consolidação, e como as diferentes bases de dados se relacionam entre si;
- um delineamento preliminar do problema, ainda sem solução definida (projeto novo — não
  entra em ideação/solução nesta etapa).

## O que esta etapa entrega

O grupo quer ir além da citação de números do PSVR e dos relatórios institucionais, e
**trabalhar diretamente com os dados brutos** por trás desses números. Isso significa:

1. Catalogar, de forma rastreável, todo dataset público relevante (feito — ver
   `02-catalogo-de-dados.md`).
2. Entender como esses datasets se relacionam conceitualmente entre si, e onde as
   comparações diretas são inválidas (ver `03-ontologia.md` e
   `06-limitacoes-metodologicas.md`).
3. Construir um pipeline de código (a construir, fora deste pacote de contexto) que baixe
   esses dados de forma reprodutível, documente suas limitações, e deixe tudo pronto em
   formato tabular (CSV/Parquet) para análise exploratória.

Este pacote de arquivos **não é o pipeline em si** — é o contexto que um agente de código
(Claude Code) precisa para construí-lo sem redescobrir a estrutura do portal de dados do
zero. A ideia é abrir este repositório com o Claude Code e pedir a implementação com base
nos documentos aqui.

## Fora de escopo (por enquanto)

- Ideação de solução, trilha técnica ou definição de produto — o projeto é novo e essa
  discussão ainda não começou.
- Qualquer join definitivo entre bases sem validação estatística — os datasets não têm uma
  chave de junção compartilhada (ver `03-ontologia.md`).
- Dados de outros municípios da Região Metropolitana — o escopo é o Recife (embora o
  dataset do SAMU inclua chamados de outros municípios atendidos pela central metropolitana,
  o que precisa ser filtrado).
