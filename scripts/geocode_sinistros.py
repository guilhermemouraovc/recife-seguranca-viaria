"""Adds lat/lon to the cleaned sinistros (output of clean_sinistros.py).

Two sources, best first, recorded in `geo_precisao`:
  - "semaforo": num_semaforo joined to the CTTU semaforos dataset (if downloaded).
  - "via_bairro": Nominatim (OpenStreetMap) point for the street *inside that bairro* --
    a stretch of the street, not the exact spot. Fine for bairro/corridor analysis,
    NOT for "which corner" analysis (docs/06 #7).
  - "via": street found only without the bairro -- can be km away on long avenues.
Nominatim answers are cached in geocode_cache.json, so the run is resumable and
re-runs only query new (endereco, bairro) pairs. Policy: max 1 req/s.
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed" / "sinistros"
CACHE_PATH = PROC_DIR / "geocode_cache.json"
SEMAFOROS_DIR = ROOT / "data" / "raw" / "cttu" / "localizacao-dos-semaforos"
# Recife bounding box -- results outside it are rejected.
VIEWBOX = "-35.02,-7.92,-34.85,-8.16"
# Only the leading street-type abbreviations; Nominatim handles the rest.
ABREV = {"AV": "AVENIDA", "R": "RUA", "EST": "ESTRADA", "PCA": "PRACA", "PRC": "PRACA",
         "TV": "TRAVESSA", "TRAV": "TRAVESSA", "ROD": "RODOVIA", "LGO": "LARGO", "VD": "VIADUTO",
         "VDO": "VIADUTO", "AL": "ALAMEDA", "PRQ": "PARQUE", "LAD": "LADEIRA", "PTE": "PONTE"}


def _expand(endereco: str) -> str:
    first, _, rest = endereco.partition(" ")
    return f"{ABREV.get(first, first)} {rest}".strip()


_last_call = 0.0


def nominatim(query: str) -> dict | None:
    global _last_call
    time.sleep(max(0.0, _last_call + 1.05 - time.monotonic()))  # Nominatim policy: max 1 req/s
    _last_call = time.monotonic()
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "br",
                "viewbox": VIEWBOX, "bounded": 1},
        headers={"User-Agent": "recife-seguranca-viaria/0.1 (projeto academico CESAR School)"},
        timeout=30,
    )
    response.raise_for_status()
    hits = response.json()
    return {"lat": float(hits[0]["lat"]), "lon": float(hits[0]["lon"]),
            "display_name": hits[0]["display_name"]} if hits else None


def geocode(endereco: str, bairro: str) -> dict | None:
    hit = nominatim(f"{_expand(endereco)}, {bairro}, Recife, PE")
    if hit:
        return hit | {"precisao": "via_bairro"}
    hit = nominatim(f"{_expand(endereco)}, Recife, PE")
    return hit | {"precisao": "via"} if hit else None


def geocode_pairs(pairs: pd.DataFrame, cache: dict) -> None:
    todo = [(e, b) for e, b in pairs.itertuples(index=False) if f"{e}|{b}" not in cache]
    print(f"{len(todo)} (endereco, bairro) pairs to geocode (~{len(todo) // 60} min)")
    for i, (endereco, bairro) in enumerate(todo, 1):
        try:
            cache[f"{endereco}|{bairro}"] = geocode(endereco, bairro)
        except requests.RequestException as err:
            print(f"  network error, stopping (cache kept): {err}", file=sys.stderr)
            break
        if i % 50 == 0:
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False))
            print(f"  {i}/{len(todo)}", flush=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False))


def semaforos() -> pd.DataFrame | None:
    csvs = sorted(SEMAFOROS_DIR.glob("semaforos*.csv"))
    if not csvs:
        print("semaforos not downloaded -- run fetch_datasets.py --dataset semaforos (skipping)")
        return None
    s = pd.read_csv(csvs[0], sep=";", decimal=",", dtype={"semaforo": "Int64"})
    return s[["semaforo", "latitude", "longitude"]].dropna().drop_duplicates("semaforo")


if __name__ == "__main__":
    df = pd.read_parquet(PROC_DIR / "sinistros_2015_2024.parquet")
    cache = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
    if "--retry-misses" in sys.argv:  # e.g. after adding an abbreviation to ABREV
        cache = {k: v for k, v in cache.items() if v}
    pairs = df[["endereco", "bairro"]].dropna().drop_duplicates()
    if "--offline" not in sys.argv:
        geocode_pairs(pairs, cache)

    df["lat"] = pd.NA
    df["lon"] = pd.NA
    df["geo_precisao"] = pd.NA
    hits = df["endereco"].str.cat(df["bairro"], sep="|").map(cache)
    found = hits.notna()
    df.loc[found, "lat"] = hits[found].map(lambda h: h["lat"])
    df.loc[found, "lon"] = hits[found].map(lambda h: h["lon"])
    df.loc[found, "geo_precisao"] = hits[found].map(lambda h: h["precisao"])

    sem = semaforos()
    if sem is not None:
        m = df[["num_semaforo"]].merge(sem, left_on="num_semaforo", right_on="semaforo", how="left")
        ok = m["latitude"].notna().to_numpy()
        df.loc[ok, "lat"] = m.loc[ok, "latitude"].to_numpy()
        df.loc[ok, "lon"] = m.loc[ok, "longitude"].to_numpy()
        df.loc[ok, "geo_precisao"] = "semaforo"

    df["lat"] = df["lat"].astype("Float64")
    df["lon"] = df["lon"].astype("Float64")
    df.to_parquet(PROC_DIR / "sinistros_2015_2024_geo.parquet", index=False)
    print(df["geo_precisao"].value_counts(dropna=False).to_string())
