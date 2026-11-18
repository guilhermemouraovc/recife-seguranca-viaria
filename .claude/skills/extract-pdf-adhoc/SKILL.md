---
name: extract-pdf-adhoc
description: Extrai texto e tabelas brutas de PDFs avulsos que um aluno do grupo queira explorar, sem usar IA/OCR (pdfplumber, camada de texto nativa do PDF). Use quando o usuário pedir para "extrair um PDF", "rodar extração ad-hoc de PDF", "ler esse PDF em texto/tabela", ou similar, fora do fluxo dos PDFs institucionais (PSVR/Relatórios Anuais, que já têm pipeline própria em scripts/fetch_pdfs.py + scripts/extract_pdfs.py).
---

# Extração ad-hoc de PDF

Extração 100% determinística via `pdfplumber` (texto/tabela nativos do PDF) — nenhuma
chamada de IA/LLM/OCR acontece na extração em si. O agente só orquestra: cria a pasta,
roda o script, reporta o resultado.

## Passos

1. Crie a pasta de entrada se não existir: `mkdir -p data/adhoc/raw`.
2. Se o usuário já apontou um arquivo/pasta de origem, copie o(s) PDF(s) para
   `data/adhoc/raw/`. Caso contrário, diga a ele para soltar o(s) PDF(s) nessa pasta e
   avisar quando terminar — não fique tentando adivinhar ou esperando em loop.
3. Rode: `.venv/bin/python scripts/extract_adhoc.py`.
4. Reporte por arquivo: quantidade de caracteres extraídos, e o aviso de páginas
   rasterizadas se aparecer (significa PDF escaneado/"Print to PDF" sem camada de texto
   real — isso não tem solução sem OCR, que está fora do escopo desta skill; avise o
   usuário em vez de tentar contornar).
5. Aponte a saída: `data/adhoc/processed/<nome>.txt` (texto corrido) e
   `data/adhoc/processed/<nome>_tables_raw.json` (tabelas detectadas, brutas e **não
   revisadas** — mesma ressalva do resto do projeto: não "consertar" uma tabela
   incompleta ou bagunçada, apenas sinalizar).

## O que essa skill não faz

- Não interpreta tabelas de forma específica (isso é papel de quem for analisar o PDF
  depois, ou de um script dedicado como `extract_psvr_iniciativas` em
  `scripts/extract_pdfs.py` para os PDFs institucionais).
- Não baixa PDFs da internet — isso é `scripts/fetch_pdfs.py`, para as fontes já
  catalogadas em `docs/02-catalogo-de-dados.md`.
- `data/adhoc/` não é versionado (git-ignorado) e não é limpo automaticamente — os
  arquivos ficam acumulando entre usos do grupo.
