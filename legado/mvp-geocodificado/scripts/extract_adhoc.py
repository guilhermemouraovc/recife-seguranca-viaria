"""Extracts text and best-effort raw tables from PDFs dropped in data/adhoc/raw/,
using the same pdfplumber-based logic as extract_pdfs.py (no institutional-specific
table parsing, no OCR/AI -- text-layer extraction only). See
.claude/skills/extract-pdf-adhoc/SKILL.md.
"""
from pathlib import Path

from extract_pdfs import extract_raw_tables, extract_text

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "adhoc" / "raw"
OUT_DIR = ROOT / "data" / "adhoc" / "processed"


def process(pdf_path: Path) -> None:
    import json

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem
    print(f"{stem}:")

    text, rasterized_pages, total_pages = extract_text(pdf_path)
    (OUT_DIR / f"{stem}.txt").write_text(text, encoding="utf-8")
    print(f"  text -> {stem}.txt ({len(text)} chars)")
    if rasterized_pages:
        print(f"  WARNING: {rasterized_pages}/{total_pages} pages have no text layer "
              f"(rasterized/scanned) -- extraction cannot recover these without OCR")

    raw_tables = extract_raw_tables(pdf_path)
    (OUT_DIR / f"{stem}_tables_raw.json").write_text(
        json.dumps(raw_tables, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  raw tables -> {stem}_tables_raw.json ({len(raw_tables)} tables, unreviewed)")


if __name__ == "__main__":
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"no PDFs found in {RAW_DIR} -- drop a PDF there first")
    for pdf_path in pdfs:
        process(pdf_path)
    print(f"done -- output in {OUT_DIR}")
