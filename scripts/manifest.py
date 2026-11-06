"""Provenance manifest for downloaded resources (data/manifest.jsonl).

Each line records one downloaded resource so re-runs can skip files that
haven't changed upstream (matched by resource_id + last_modified) and so
silent source updates are detectable later via sha256.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "manifest.jsonl"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path = DEFAULT_PATH) -> dict[str, dict]:
    """Latest manifest entry per resource_id (later lines override earlier ones)."""
    if not path.exists():
        return {}
    entries: dict[str, dict] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entry = json.loads(line)
                entries[entry["resource_id"]] = entry
    return entries


def needs_download(entries: dict[str, dict], resource: dict, force: bool = False) -> bool:
    """True if `resource` (a CKAN resource dict) hasn't been fetched yet, or changed since."""
    if force:
        return True
    previous = entries.get(resource["id"])
    if previous is None:
        return True
    return previous.get("resource_last_modified") != resource.get("last_modified")


def record(
    path: Path,
    *,
    dataset_slug: str,
    resource: dict,
    source_url: str,
    local_path: Path,
    package_metadata_snapshot: dict | None = None,
) -> dict:
    """Append one entry to the manifest and return it."""
    entry = {
        "dataset_slug": dataset_slug,
        "resource_id": resource["id"],
        "resource_name": resource.get("name"),
        "resource_last_modified": resource.get("last_modified"),
        "source_url": source_url,
        "format": resource.get("format"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256_file(local_path),
        "local_path": str(local_path),
        "package_metadata_snapshot": package_metadata_snapshot,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.jsonl"
        sample_file = tmp_path / "sample.csv"
        sample_file.write_text("a;b\n1;2\n")

        resource = {"id": "res-1", "name": "Sample", "format": "CSV", "last_modified": "2026-01-01T00:00:00"}
        assert needs_download({}, resource) is True

        record(manifest_path, dataset_slug="test-dataset", resource=resource,
               source_url="https://example.org/sample.csv", local_path=sample_file)

        entries = load(manifest_path)
        assert not needs_download(entries, resource), "unchanged resource should be skipped"

        resource_updated = {**resource, "last_modified": "2026-02-01T00:00:00"}
        assert needs_download(entries, resource_updated), "changed last_modified should re-download"
        assert needs_download(entries, resource, force=True), "--force should always re-download"

        print("manifest self-check passed")
