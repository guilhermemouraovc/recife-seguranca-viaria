"""Minimal client for the CKAN API at dados.recife.pe.gov.br.

Resource `url` values from package_show point at a stable dados.recife.pe.gov.br
download link that 302-redirects to a signed URL (~1h expiry). Always resolve
via package_show right before downloading -- never cache the signed URL.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://dados.recife.pe.gov.br/api/3/action"


def _session() -> requests.Session:
    session = requests.Session()
    # No documented rate limit -- retry with backoff covers transient errors
    # and bursts without needing a custom rate limiter.
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


_SESSION = _session()


def _call(action: str, **params) -> dict:
    response = _SESSION.get(f"{BASE_URL}/{action}", params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"CKAN API error on {action}: {payload}")
    return payload["result"]


def package_search(organization: str | None = None, query: str | None = None, rows: int = 100) -> list[dict]:
    """List datasets, optionally filtered by organization slug or free-text query."""
    params = {"rows": rows}
    if organization:
        params["fq"] = f"organization:{organization}"
    if query:
        params["q"] = query
    return _call("package_search", **params)["results"]


def package_show(dataset_slug: str) -> dict:
    """Full metadata for one dataset, including its `resources` list."""
    return _call("package_show", id=dataset_slug)


def organization_list() -> list[str]:
    return _call("organization_list")


if __name__ == "__main__":
    # Smoke test against the real API -- requires network.
    pkg = package_show("acidentes-de-transito-com-e-sem-vitimas")
    assert pkg["resources"], "expected at least one resource"
    print(f"{pkg['title']}: {len(pkg['resources'])} resources")
