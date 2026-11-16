# Downloads the PSVR PDF (direct URL) and the 5 Relatórios Anuais PDFs (Google Drive).
"""Downloads the 2 institutional PDF sources into data/raw/pdf/, using manifest for
idempotency. See docs/02-catalogo-de-dados.md section F.
"""
import argparse
import re
from pathlib import Path

import requests

import manifest as manifest_mod

PDF_DIR = manifest_mod.ROOT / "data" / "raw" / "pdf"

PSVR_URL = "https://cttu.recife.pe.gov.br/sites/default/files/2026-06/PSVR%20%28REV07%29%20_0.pdf"

# Drive file IDs collected from https://cttu.recife.pe.gov.br/relatorios-anuais-de-seguranca-viaria,
# in page order. Year for each confirmed by opening the downloaded PDF (not guessed):
#   2020 -- cover page text reads "RELATORIO ANUAL DE SEGURANCA VIARIA / RECIFE 2020"
#   2021 -- PDF metadata Title: "Relatorio anual de vitimas de transito 2021 07.11.22.indd"
#   2022 -- Drive virus-scan warning page names the file "...dados de 2022.pdf" (163M, too
#           large to scan -- this is the one requiring the confirm-form flow below)
#   2023 -- PDF metadata Title: "Relatorio anual de vitimas de transito 2023 (10.06.25).indd"
#   2024 -- PDF metadata Title: "Relatorio anual de vitimas de transito 2024.indd"
DRIVE_ID_TO_YEAR = {
    "1eHS78nMNuA773CDHjwewQn4Bkrly_w7p": 2020,
    "1ckXF6eEmKx8gZZrCHSJ-WF504VX3C2ST": 2021,
    "16_ADl5iRB9OUPo2ulL_F50Lk1Gc762Ll": 2022,
    "1idoN6SJARUBZSeU6hnL_3rhFuIo_2L5R": 2023,
    "1V8bQbyg0flkcG-OMkrn6rSBeqt_Ygkvh": 2024,
}


def _drive_resource(file_id: str, year: int) -> dict:
    # Drive has no reliable last_modified for these files -- last_modified=None on
    # both sides means needs_download() only re-fetches on --force (see manifest.py).
    return {"id": f"drive-{file_id}", "name": f"relatorio_anual_{year}", "format": "PDF", "last_modified": None}


def _psvr_resource() -> dict:
    return {"id": "psvr-2026-2036", "name": "psvr_2026_2036", "format": "PDF", "last_modified": None}


def _download_drive_file(file_id: str, session: requests.Session) -> bytes:
    """Fetch a public Drive file by ID, handling the large-file virus-scan warning page."""
    url = "https://drive.google.com/uc"
    params = {"id": file_id, "export": "download"}
    response = session.get(url, params=params, timeout=120)
    response.raise_for_status()

    if "text/html" in response.headers.get("Content-Type", ""):
        # Warning page for files Drive can't virus-scan: a "Download anyway" form with
        # hidden id/export/confirm/uuid inputs posting to drive.usercontent.google.com.
        form_match = re.search(r'<form[^>]*action="([^"]+)"[^>]*>(.*?)</form>', response.text, re.S)
        if form_match is None:
            raise RuntimeError(f"Drive file {file_id}: got HTML warning page but no download form found")
        action_url = form_match.group(1)
        form_params = dict(re.findall(r'name="([^"]+)"\s+value="([^"]*)"', form_match.group(2)))
        response = session.get(action_url, params=form_params, timeout=120)
        response.raise_for_status()

    if "text/html" in response.headers.get("Content-Type", ""):
        raise RuntimeError(f"Drive file {file_id}: still got HTML after confirm-form retry")

    return response.content


def fetch_psvr(force: bool = False) -> Path | None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    entries = manifest_mod.load()
    resource = _psvr_resource()
    if not manifest_mod.needs_download(entries, resource, force=force):
        print("psvr_2026_2036.pdf: unchanged, skipping")
        return None

    local_path = PDF_DIR / "psvr_2026_2036.pdf"
    response = requests.get(PSVR_URL, timeout=120)
    response.raise_for_status()
    local_path.write_bytes(response.content)
    manifest_mod.record(
        manifest_mod.DEFAULT_PATH,
        dataset_slug="psvr",
        resource=resource,
        source_url=PSVR_URL,
        local_path=local_path,
    )
    print(f"  {local_path}")
    return local_path


def fetch_relatorios(force: bool = False) -> list[Path]:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    entries = manifest_mod.load()
    session = requests.Session()
    downloaded = []
    for file_id, year in DRIVE_ID_TO_YEAR.items():
        resource = _drive_resource(file_id, year)
        if not manifest_mod.needs_download(entries, resource, force=force):
            print(f"relatorio_anual_{year}.pdf: unchanged, skipping")
            continue
        local_path = PDF_DIR / f"relatorio_anual_{year}.pdf"
        content = _download_drive_file(file_id, session)
        local_path.write_bytes(content)
        source_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        manifest_mod.record(
            manifest_mod.DEFAULT_PATH,
            dataset_slug="relatorios-anuais-seguranca-viaria",
            resource=resource,
            source_url=source_url,
            local_path=local_path,
        )
        downloaded.append(local_path)
        print(f"  {local_path}")
    return downloaded


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download even if unchanged")
    args = parser.parse_args()

    print("PSVR 2026-2036:")
    fetch_psvr(force=args.force)
    print("Relatorios Anuais de Seguranca Viaria:")
    fetch_relatorios(force=args.force)
