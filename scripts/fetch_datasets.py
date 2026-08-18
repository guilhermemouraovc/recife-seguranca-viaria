"""Downloads CTTU/SAMU CKAN datasets (CSV/JSON) into data/raw/, using ckan_client + manifest."""
import argparse
import re
from pathlib import Path

import requests

import ckan_client
import manifest as manifest_mod

RAW_DIR = manifest_mod.ROOT / "data" / "raw"

# Section A of docs/02-catalogo-de-dados.md. registro-de-chamados-atendidos-pela-cttu
# is excluded -- its scope ("chamados gerais" vs. just sinistros) isn't confirmed yet.
SINISTROS_SLUGS = [
    "acidentes-de-transito-com-e-sem-vitimas",
    "acidentes-de-transito-com-vitimas-2014",
    "acidentes-de-transito-com-vitimas-2015",
    "acidentes-de-transito-c-vitimas-2016",
]


def _safe_filename(name: str, fmt: str) -> str:
    slug = re.sub(r"[^\w\-]+", "_", name.strip()).strip("_").lower()
    ext = (fmt or "").lower() or "bin"
    return f"{slug}.{ext}"


def fetch_dataset(slug: str, org_dir: str, force: bool = False) -> list[Path]:
    """Download every resource of one CKAN dataset into data/raw/<org_dir>/<slug>/."""
    package = ckan_client.package_show(slug)
    dest_dir = RAW_DIR / org_dir / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    entries = manifest_mod.load()
    downloaded = []
    for resource in package["resources"]:
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


def fetch_sinistros(force: bool = False) -> None:
    for slug in SINISTROS_SLUGS:
        print(f"{slug}:")
        fetch_dataset(slug, org_dir="cttu", force=force)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download even if unchanged")
    parser.add_argument("--dataset", choices=["sinistros"], default="sinistros")
    args = parser.parse_args()

    if args.dataset == "sinistros":
        fetch_sinistros(force=args.force)
