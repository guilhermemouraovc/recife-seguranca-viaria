# Handoff — PDF download + text/table extraction

Self-contained brief for a fresh Claude Code conversation in this same repo. You
were not part of the conversation that set this up — everything you need is
here or in `docs/`. Read `CLAUDE.md` first (repo-wide rules), then this file.

## Goal

Download the 2 institutional PDF sources and extract usable text/tables from
them. This is docs/07's task T4, scoped down to just the PDF side (the CSV/CKAN
dataset extraction is being handled in a separate, parallel conversation — do
not touch `scripts/ckan_client.py`, `scripts/fetch_datasets.py`, or
`data/raw/cttu|samu/` unless a conflict forces it).

## What already exists — reuse it, don't rebuild

- **`scripts/manifest.py`** — provenance/idempotency module, already built and
  tested. Use `manifest.load()`, `manifest.needs_download()`,
  `manifest.record()`, `manifest.sha256_file()`. It expects a CKAN-shaped
  resource dict (`{"id": ..., "name": ..., "format": ..., "last_modified": ...}`)
  — for Drive files there's no reliable `last_modified`, so synthesize one:
  `{"id": "<stable-slug>", "name": "...", "format": "PDF", "last_modified": None}`.
  With `last_modified=None` on both sides, re-runs will correctly skip
  already-downloaded files (see `needs_download` logic) — only `--force`
  re-downloads them.
- **Path convention**: every script anchors paths to the repo root via
  `ROOT = Path(__file__).resolve().parent.parent`, never a bare relative
  `Path("data/...")` — a real bug already happened here from resolving paths
  against `cwd` instead. Follow the same pattern (see `manifest.py`'s `ROOT`).
- **`scripts/fetch_pdfs.py`** — currently just a header-comment stub. This is
  where the download logic goes.
- **venv**: `.venv/` already exists at repo root with `requests`, `pandas`,
  `pyarrow` installed. Use `.venv/bin/python`, `.venv/bin/pip install ...` —
  don't `pip install` into system Python (it's externally managed and will
  refuse). Add `pdfplumber` to `requirements.txt` and install it into `.venv`
  for the extraction step (no PDF library is installed yet — confirmed by
  testing `pdfplumber`/`pypdf`/`PyPDF2`/`fitz`, none present).

## Sources (from docs/02-catalogo-de-dados.md, section F)

**PSVR 2026–2036** — direct, stable URL, no auth/redirect games:
```
https://cttu.recife.pe.gov.br/sites/default/files/2026-06/PSVR%20%28REV07%29%20_0.pdf
```

**5 Relatórios Anuais de Segurança Viária** — hosted on Google Drive, not the
CKAN portal. File IDs collected so far:
```
1eHS78nMNuA773CDHjwewQn4Bkrly_w7p
1ckXF6eEmKx8gZZrCHSJ-WF504VX3C2ST
16_ADl5iRB9OUPo2ulL_F50Lk1Gc762Ll
1idoN6SJARUBZSeU6hnL_3rhFuIo_2L5R
1V8bQbyg0flkcG-OMkrn6rSBeqt_Ygkvh
```
Download pattern: `https://drive.google.com/uc?export=download&id=<ID>`.
**Only 3 of the 5 years are guessed** (probably 2020, 2021, 2022) — the last 2
are NOT identified. Do not assume; open each downloaded PDF, read the cover
page / header for the actual year, and record the mapping explicitly (e.g. in
a comment or a small `id_to_year` dict with a citation of what you saw on the
page — not a guess).

**Large-file confirmation token**: Drive serves a virus-scan warning page
instead of the file for files it can't scan, requiring a second request with a
`confirm=<token>` param. Handle this — don't assume `uc?export=download` alone
always returns the PDF bytes; check the `Content-Type` of the response (an
`html` response means you got the warning page, not the PDF) and follow the
confirm-token flow when that happens.

## What "done" looks like

1. `scripts/fetch_pdfs.py` downloads all 6 PDFs into `data/raw/pdf/` (suggested
   names: `psvr_2026_2036.pdf`, `relatorio_anual_<year-or-index>.pdf`), records
   each in `data/manifest.jsonl` via the shared `manifest` module, and is
   idempotent on re-run (matches the pattern already proven in
   `scripts/fetch_datasets.py` — verify by running it twice and confirming the
   second run downloads nothing).
2. A extraction step (can live in the same script or a new
   `scripts/extract_pdfs.py`) that pulls plain text from each PDF with
   `pdfplumber`, and attempts table extraction for the PSVR's
   metas/indicadores tables and the Relatórios Anuais' historical
   mortes/feridos series (docs/03-ontologia.md and docs/04-esquemas-datasets.md
   both flag these as the two things worth extracting from the PDFs — full
   text is a fallback for everything else, not the primary goal).
3. Output goes to `data/processed/pdf/` — plain text per PDF at minimum, plus
   whatever table extraction succeeds (CSV/JSON, doesn't need to be pretty).
4. **Table extraction is unreliable — say so, don't hide it.** If a table
   comes out garbled or incomplete, note that in the output/README rather than
   silently dropping rows or "fixing" values by inference. Per
   `docs/06-limitacoes-metodologicas.md`'s overall rule for this project: known
   data-quality issues get flagged, never silently corrected.
5. One runnable smoke check (matches the style of `scripts/manifest.py`'s
   `__main__` block and `scripts/ckan_client.py`'s `__main__` block) —
   doesn't need to be a full test suite, just something that fails loudly if
   the download or extraction logic breaks.

## Style/scope notes carried over from the rest of this pipeline

- Lazy/minimal: `requests` + `pdfplumber`, no PDF processing framework, no
  OCR pipeline (these PDFs are text-based, not scanned, per docs/02).
- No new abstractions beyond what this needs — this project is small and has
  an academic deadline; match the plain-function style already in
  `scripts/ckan_client.py` and `scripts/manifest.py`, not a class hierarchy.
- Don't touch `docs/07-backlog-tarefas.md`'s numbering or the other tasks
  (#5–#8, #11–#13 in the parallel conversation's tracker) — this handoff only
  covers T4 (PDFs).
