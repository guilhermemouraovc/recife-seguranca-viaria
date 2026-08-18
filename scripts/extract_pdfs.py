"""Extracts text and best-effort tables from the institutional PDFs (PSVR + Relatórios
Anuais) into data/processed/pdf/. Table extraction is unreliable, especially for the
Relatórios Anuais (InDesign infographic layouts, not data grids) -- garbled/incomplete
tables are kept and flagged in the README, never silently corrected. See
docs/06-limitacoes-metodologicas.md.
"""
import json
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "pdf"
OUT_DIR = ROOT / "data" / "processed" / "pdf"

# Pages (0-indexed) in psvr_2026_2036.pdf holding the AÇÕES / ÓRGÃOS RESPONSÁVEIS /
# INDICADOR tables for governança + the 4 eixos -- located by scanning find_tables()
# output for that exact header row, not guessed.
PSVR_INICIATIVAS_PAGES = [18, 19, 21, 22, 23, 25, 26, 28, 29, 30, 32, 33, 34]

README_TEXT = """\
# PDFs institucionais extraídos (PSVR + Relatórios Anuais)

Gerado por `scripts/extract_pdfs.py` a partir dos PDFs em `data/raw/pdf/`
(baixados por `scripts/fetch_pdfs.py`).

## Conteúdo

- `<nome>.txt` — texto corrido de cada PDF, página a página (separador `\\f`).
- `psvr_iniciativas.json` — tabela AÇÕES / ÓRGÃOS RESPONSÁVEIS / INDICADOR do PSVR,
  uma linha por ação, com a seção (eixo/iniciativa) de origem. Extração limpa —
  tabelas com grade real no PDF.
- `<nome>_tables_raw.json` — despejo bruto de toda tabela que o pdfplumber detectou
  em cada página, sem interpretação. Fallback para o que não está em
  `psvr_iniciativas.json`.

## Limitações conhecidas (não corrigidas, apenas sinalizadas)

- **3 dos 5 Relatórios Anuais (2021, 2023, 2024) não têm camada de texto — são PDFs
  rasterizados.** Foram gerados via "Microsoft: Print To PDF" (ver metadado `Producer`
  de cada arquivo) e cada página é uma imagem, não texto real: `page.chars` é 0 em
  todas as páginas verificadas, apesar de haver `page.images`. O `.txt` desses 3
  arquivos fica praticamente vazio (algumas dezenas de caracteres de metadado). Isso
  **contradiz a suposição de `docs/02-catalogo-de-dados.md` de que os PDFs são texto
  corrido, não digitalizados** — vale atualizar aquele documento. OCR está fora do
  escopo definido no handoff desta tarefa; não foi implementado aqui. Os relatórios de
  **2020 e 2022** (Adobe InDesign / Adobe PDF Library) têm texto real e extraíram bem
  (83k e 91k caracteres).
- **Extração de tabela é não confiável para os Relatórios Anuais.** Esses PDFs usam
  layout de infográfico (Adobe InDesign / Print-to-PDF), com texto de gráficos e
  caixas de destaque sobrepostos às tabelas de dados reais. O `find_tables()` do
  pdfplumber frequentemente retorna fragmentos de texto decorativo misturados com
  números da tabela, não uma grade limpa — ver `*_tables_raw.json` dos
  `relatorio_anual_*`, cujas linhas exigem revisão manual antes de qualquer uso.
  As séries históricas "vítimas feridas/fatais por tipo de usuário" (ex.: Tabela 03
  e Tabela 12 do relatório de 2020) existem no texto corrido (`.txt`) mesmo quando a
  extração de tabela falha.
- **Ano de cada Relatório Anual** foi confirmado abrindo o PDF (capa/metadado), não
  suposto — ver comentário em `scripts/fetch_pdfs.py` (`DRIVE_ID_TO_YEAR`).
- **Cobertura parcial de 2015**: o dataset de sinistros CTTU só tem dados de 2015 a
  partir de junho — qualquer número de 2015 nos Relatórios Anuais ou no PSVR que
  cite esse ano deve ser lido com essa ressalva.
- **"Chamados" ≠ "registros estatísticos dos relatórios anuais"**: os números destes
  PDFs vêm de registros estatísticos de agentes de trânsito, um processo de coleta
  diferente do dataset CKAN de "chamados" de sinistro — não tratar como a mesma fonte
  de verdade, mesmo quando os números parecerem próximos.
- **Dados de 2025 são preliminares**: o PSVR usa 2025 como ano-base (140 vítimas
  fatais, 5.930 feridas) mas o próprio programa classifica esses números como
  preliminares (fonte COMPAT/SDS e SAMU Recife, ver página 12 do PSVR).
"""


def extract_text(pdf_path: Path) -> tuple[str, int, int]:
    """Returns (text, pages_with_no_chars, total_pages). A page with images but zero
    chars means it's a rasterized scan/export, not real text -- extract_text() can't
    recover that without OCR (explicitly out of scope, see docs/07 handoff)."""
    with pdfplumber.open(pdf_path) as pdf:
        rasterized = sum(1 for page in pdf.pages if len(page.chars) == 0 and len(page.images) > 0)
        text = "\n\f\n".join(page.extract_text() or "" for page in pdf.pages)
        return text, rasterized, len(pdf.pages)


def extract_psvr_iniciativas(pdf_path: Path) -> list[dict]:
    """Rows of the eixo/iniciativa AÇÕES table, tagged with the page's section header
    (the table itself doesn't repeat eixo/iniciativa per row)."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in PSVR_INICIATIVAS_PAGES:
            page = pdf.pages[page_num]
            header_line = (page.extract_text() or "").split("\n")[0]
            for table in page.find_tables():
                data = table.extract()
                if not data or data[0][:3] != ["AÇÕES", "ÓRGÃOS RESPONSÁVEIS", "INDICADOR"]:
                    continue
                for row in data[1:]:
                    if not any(row):
                        continue
                    rows.append({
                        "page": page_num,
                        "secao": header_line,
                        "acao": row[0],
                        "orgaos_responsaveis": row[1],
                        "indicador": row[2],
                    })
    return rows


def extract_raw_tables(pdf_path: Path) -> list[dict]:
    """Every table pdfplumber detects, page by page, no interpretation applied."""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            for table_idx, table in enumerate(page.find_tables()):
                tables.append({"page": page_num, "table_index": table_idx, "rows": table.extract()})
    return tables


def process(pdf_path: Path) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem
    print(f"{stem}:")

    text, rasterized_pages, total_pages = extract_text(pdf_path)
    (OUT_DIR / f"{stem}.txt").write_text(text, encoding="utf-8")
    print(f"  text -> {stem}.txt ({len(text)} chars)")
    if rasterized_pages:
        print(f"  WARNING: {rasterized_pages}/{total_pages} pages have no text layer "
              f"(rasterized/scanned export) -- text extraction cannot recover these "
              f"pages without OCR (out of scope, see data/processed/pdf/README.md)")

    if stem == "psvr_2026_2036":
        rows = extract_psvr_iniciativas(pdf_path)
        (OUT_DIR / "psvr_iniciativas.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  iniciativas table -> psvr_iniciativas.json ({len(rows)} rows)")

    raw_tables = extract_raw_tables(pdf_path)
    (OUT_DIR / f"{stem}_tables_raw.json").write_text(
        json.dumps(raw_tables, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  raw tables -> {stem}_tables_raw.json ({len(raw_tables)} tables, unreviewed -- see README)")


if __name__ == "__main__":
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit("no PDFs found in data/raw/pdf/ -- run fetch_pdfs.py first")
    for pdf_path in pdfs:
        process(pdf_path)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "README.md").write_text(README_TEXT, encoding="utf-8")

    # smoke check: PSVR text and iniciativas table must be non-trivial
    psvr_text = (OUT_DIR / "psvr_2026_2036.txt").read_text(encoding="utf-8")
    assert len(psvr_text) > 10000, "PSVR text extraction looks truncated"
    iniciativas = json.loads((OUT_DIR / "psvr_iniciativas.json").read_text(encoding="utf-8"))
    assert len(iniciativas) > 10, "PSVR iniciativas table extraction looks empty/broken"
    print("extract_pdfs self-check passed")
