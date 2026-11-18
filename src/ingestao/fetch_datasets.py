"""Downloads the yearly sinistros CSVs (2015-2024) from the Recife CKAN portal into data/raw/.

Only the acidentes-de-transito-com-e-sem-vitimas dataset, and only its CSV resources
(ARCHITECTURE.md, section 2.1). Uses ckan_client + manifest for provenance and re-run skipping.
"""
import argparse
import re
from pathlib import Path

import requests

from src.ingestao import ckan_client
from src.ingestao import manifest as manifest_mod

RAW_DIR = manifest_mod.ROOT / "data" / "raw"

SLUG = "acidentes-de-transito-com-e-sem-vitimas"


def _safe_filename(name: str, fmt: str) -> str:
    slug = re.sub(r"[^\w\-]+", "_", name.strip()).strip("_").lower()
    ext = (fmt or "").lower() or "bin"
    return f"{slug}.{ext}"


def fetch_dataset(slug: str, org_dir: str, force: bool = False) -> list[Path]:
    """Download the CSV resources of one CKAN dataset into data/raw/<org_dir>/<slug>/."""
    package = ckan_client.package_show(slug)
    dest_dir = RAW_DIR / org_dir / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    entries = manifest_mod.load()
    downloaded = []
    for resource in package["resources"]:
        # The dataset also ships a JSON data dictionary; only the yearly CSVs are data.
        if (resource.get("format") or "").upper() != "CSV":
            continue
        if not manifest_mod.needs_download(entries, resource, force=force):
            continue
        local_path = dest_dir / _safe_filename(resource.get("name") or resource["id"], resource.get("format", ""))
        # resource["url"] is the stable dados.recife.pe.gov.br link; it 302s to a
        # signed URL that expires in ~1h -- resolved fresh on every request, never cached.
        response = requests.get(resource["url"], timeout=120, allow_redirects=True)
        response.raise_for_status()
        local_path.write_bytes(response.content)
        manifest_mod.record(
            manifest_mod.DEFAULT_PATH,
            dataset_slug=slug,
            resource=resource,
            source_url=resource["url"],
            local_path=local_path,
            package_metadata_snapshot={
                "license_title": package.get("license_title"),
                "notes": package.get("notes"),
            },
        )
        downloaded.append(local_path)
        print(f"  {local_path}")
    return downloaded


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download even if unchanged")
    args = parser.parse_args()
    print(f"{SLUG}:")
    fetch_dataset(SLUG, org_dir="cttu", force=args.force)
