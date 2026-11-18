# 05 — Arquitetura sugerida para o pipeline de extração

Este documento é uma proposta de arquitetura, não uma implementação — o código deve ser
escrito depois de ler isto, com liberdade para ajustar detalhes.

## Princípio geral

Preferir a **API do CKAN** (`package_show`) a qualquer scraping de HTML. Todos os datasets
catalogados em `02-catalogo-de-dados.md`, exceto os PDFs institucionais, são acessíveis via
API estruturada. Reservar scraping/parsing de HTML só para as duas páginas da CTTU
mencionadas no catálogo (e mesmo assim, só para extrair links, não conteúdo).

## Particularidade importante: URLs de download são assinadas e expiram

O `url` de cada `resource` retornado por `package_show` aponta para
`dados.recife.pe.gov.br/dataset/.../download/...`, que faz um **redirect 302** para uma URL
assinada em `ckan-storage-download.app.emprel.gov.br` com parâmetros `X-Amz-Date` /
`X-Amz-Expires=3600`. Ou seja:

- A URL assinada expira em ~1 hora — **não vale a pena persistir essa URL final num
  manifesto para reuso posterior**.
- A URL "pública" (`dados.recife.pe.gov.br/.../download/...`) é estável e pode ser guardada
  no manifesto — ela sempre re-gera um redirect novo quando acessada.
- O client HTTP usado precisa seguir redirects automaticamente (`requests.get(url,
  allow_redirects=True)` já faz isso por padrão).

## Estrutura de pastas sugerida

```
data/
  raw/
    <organizacao>/<dataset-slug>/<ano-ou-recurso>.csv   # download bruto, sem alteração
    pdf/psvr_2026_2036.pdf
    pdf/relatorio_anual_<ano-ou-indice>.pdf
  processed/
    <dataset-slug>.parquet                              # já limpo/tipado, se aplicável
  manifest.json                                          # ver abaixo
```

## Manifesto de proveniência

Cada download deve registrar, num `manifest.json` (ou `.jsonl` para append incremental):

```json
{
  "dataset_slug": "acidentes-de-transito-com-e-sem-vitimas",
  "resource_id": "87ac4237-...",
  "resource_name": "Acidentes de Trânsito 2024",
  "source_url": "https://dados.recife.pe.gov.br:443/dataset/.../download/....csv",
  "format": "CSV",
  "fetched_at": "<timestamp ISO 8601>",
  "sha256": "<checksum do arquivo baixado>",
  "local_path": "data/raw/cttu/acidentes-de-transito-com-e-sem-vitimas/2024.csv",
  "package_metadata_snapshot": { "license_title": "...", "notes": "..." }
}
```

O checksum permite detectar quando um dataset foi atualizado silenciosamente pela fonte
(comum em portais CKAN — o recurso do ano corrente é sobrescrito, não versionado).

## Fluxo sugerido por tipo de fonte

**Datasets CKAN (CSV/JSON):** `package_show(slug)` → iterar `resources` → filtrar por
`format` desejado → `GET` com redirect → salvar em `raw/` com nome derivado do
`resource_name` → registrar no manifesto → (opcional) normalizar para `processed/` em
Parquet, preservando as colunas originais e documentando qualquer renomeação/tipo aplicado.

**PDFs institucionais:** o PSVR tem URL direta e estável (ver catálogo) — baixar
diretamente. Os Relatórios Anuais estão no Google Drive por ID de arquivo — resolver via
`https://drive.google.com/uc?export=download&id=<ID>`, tratando o caso de arquivo grande
que exige confirmação (`confirm=` token na resposta). Depois de baixados, extrair texto e
tabelas com a skill/ferramenta de PDF disponível no ambiente (não reimplementar parsing de
PDF do zero).

## Tratamento de encoding

Detectar encoding por arquivo em vez de assumir UTF-8 globalmente — o caso do dataset de
Equipamentos (`06-limitacoes-metodologicas.md`) mostra que a própria fonte tem bytes
corrompidos que não são UTF-8 nem Latin-1 puros (byte `0x90` solto). Uma abordagem robusta:
tentar `utf-8` estrito primeiro; se falhar, cair para `latin-1` (que nunca falha, mas pode
produzir mojibake); e, para os datasets sabidamente problemáticos, logar um aviso explícito
em vez de mascarar o problema.

## Idempotência e reprocessamento

O pipeline deve poder rodar de novo sem duplicar trabalho: pular o download se o
`resource_id` já está no manifesto com o mesmo `last_modified`/checksum reportado pela API,
e permitir um flag `--force` para re-baixar tudo.

## Bibliotecas sugeridas

`requests` (HTTP), `pandas` (tabular), `pyarrow` (Parquet), biblioteca de PDF já disponível
no ambiente de execução para os relatórios institucionais. Nada disso é obrigatório — são
as escolhas mais simples que cobrem o que este pipeline precisa fazer.
