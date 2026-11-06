"""Geocodes atropelamento addresses with Nominatim (OpenStreetMap) into a versioned cache (M1b).

This is the only script in the M1/M1b pipeline that touches the network.
build_atropelamentos.py only reads the cache it fills:
  data/geocode/cache_nominatim.csv  (versioned, so the group never repeats a query)

Input: data/processed/atropelamentos.parquet (run build_atropelamentos.py first).
Only rows without a confirmed traffic-light coordinate (coord_confere == True) are geocoded.

Nominatim usage policy (https://operations.osmfoundation.org/policies/nominatim/):
  - at most 1 request/s;
  - User-Agent identifies the project + contact from env NOMINATIM_CONTACT;
  - every query is cached (failures too) and never repeated;
  - 429/5xx -> backoff and retry (3x); 403 -> stop everything.
Ctrl+C is safe: the cache is saved every 25 queries and on exit; re-run to resume.

Geocoding (c) OpenStreetMap contributors, ODbL.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
BASE_PATH = ROOT / "data" / "processed" / "atropelamentos.parquet"
CACHE_PATH = ROOT / "data" / "geocode" / "cache_nominatim.csv"
URL = "https://nominatim.openstreetmap.org/search"
FIXED_PARAMS = {"format": "jsonv2", "addressdetails": 1, "limit": 1, "countrycodes": "br",
                "viewbox": "-35.10,-7.80,-34.80,-8.30", "bounded": 1}
MIN_INTERVAL_S = 1.1
SAVE_EVERY = 25
MAX_RETRIES = 3

# Leading street-type abbreviation in endereco_norm -> full word for the query.
# Beyond AV/R/EST/PCA/TV, the others were all observed in the sinistros addresses.
EXPANSOES = {"AV": "Avenida", "R": "Rua", "EST": "Estrada", "PCA": "Praça", "PRC": "Praça",
             "TV": "Travessa", "TRV": "Travessa", "PTE": "Ponte", "LGO": "Largo", "LAD": "Ladeira",
             "VDO": "Viaduto", "COR": "Corredor", "C": "Cais"}
TIPOS_POR_EXTENSO = {"RUA", "AVENIDA", "ESTRADA", "PRACA", "TRAVESSA", "PONTE", "LARGO", "LADEIRA",
                     "VIADUTO", "CORREDOR", "CAIS"}
AREA_KEYS = {"suburb", "neighbourhood", "quarter", "city_district", "borough", "hamlet", "village",
             "residential", "city_block", "isolated_dwelling"}
# Street types, articles and title abbreviations: they don't tell two street names apart.
TOKENS_IGNORADOS = {"RUA", "AVENIDA", "ESTRADA", "PRACA", "TRAVESSA", "PONTE", "LARGO", "LADEIRA",
                    "VIADUTO", "CORREDOR", "CAIS", "DAS", "DOS", "GOV", "ENG", "PROF", "DES", "CEL", "GAL",
                    "MAL", "CONS", "DEP", "PRES", "SEN", "VER", "MONS", "CAP", "TEN", "SGT", "DONA"}
CACHE_FIELDS = ["chave", "tentativa", "lat", "lon", "display_name", "osm_type", "osm_id", "class", "type",
                "bairro_retornado", "componentes", "nivel", "consultado_em"]


class NominatimForbidden(RuntimeError):
    """HTTP 403: the service blocked us -- never keep going after this."""


def ascii_upper(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text.upper()).strip()


def expandir_rua(endereco_norm: str, endereco: str | None = None) -> str:
    """'AV CAXANGA' -> 'Avenida CAXANGA'.

    The original endereco is used instead when it already spells the street type out
    and has no dotted abbreviations (e.g. 'RUA DIADEMA'), since it may keep accents.
    """
    original = re.sub(r"[^\w\s]", " ", endereco or "").split()
    if original and ascii_upper(original[0]) in TIPOS_POR_EXTENSO and "." not in (endereco or ""):
        return " ".join(original)
    first, _, rest = endereco_norm.partition(" ")
    return f"{EXPANSOES.get(first, first)} {rest}".strip()


def numero_valido(numero) -> str | None:
    """Only plain positive integers are sent as house numbers ('XX', 'S/N', '312A' are not)."""
    text = "" if numero is None or (isinstance(numero, float) and pd.isna(numero)) else str(numero).strip()
    return text if re.fullmatch(r"[1-9]\d*", text) else None


def tentativas(endereco_norm: str, endereco: str | None, numero, bairro) -> list[tuple[str, dict]]:
    """Ordered Nominatim queries for one address: (a) number + street, (b) street, (c) free text with bairro."""
    rua = expandir_rua(endereco_norm, endereco)
    out = []
    num = numero_valido(numero)
    if num:
        out.append(("a", {"street": f"{num} {rua}", "city": "Recife", "state": "Pernambuco"}))
    out.append(("b", {"street": rua, "city": "Recife", "state": "Pernambuco"}))
    if bairro and not (isinstance(bairro, float) and pd.isna(bairro)):
        out.append(("c", {"q": f"{rua}, {bairro}, Recife, Pernambuco"}))
    return out


def chave(params: dict) -> str:
    """Cache key: the exact query text, normalized (accents/case/spaces)."""
    return "|".join(f"{k}={ascii_upper(v)}" for k, v in sorted(params.items()))


def parse_hit(hit: dict | None) -> dict:
    """Nominatim jsonv2 result -> cache fields. nivel: numero | via | outro | falhou."""
    if not hit:
        return {"nivel": "falhou"}
    addr = hit.get("address", {})
    if addr.get("house_number"):
        nivel = "numero"
    elif hit.get("category") == "highway":
        nivel = "via"
    else:
        # A place/POI that is neither a numbered address nor a street (e.g. a suburb).
        nivel = "outro"
    return {
        "lat": hit["lat"], "lon": hit["lon"], "display_name": hit.get("display_name"),
        "osm_type": hit.get("osm_type"), "osm_id": hit.get("osm_id"),
        "class": hit.get("category"), "type": hit.get("type"),
        "bairro_retornado": addr.get("suburb") or addr.get("neighbourhood"),
        "componentes": json.dumps(addr, ensure_ascii=False), "nivel": nivel,
    }


def _componentes(componentes_json) -> dict:
    if not componentes_json or (isinstance(componentes_json, float) and pd.isna(componentes_json)):
        return {}
    return json.loads(componentes_json)


def bairro_confere(bairro, componentes_json, display_name=None) -> bool:
    """True if the sinistro bairro equals any sub-city area of the returned address.

    Checks every area level OSM may use for a Recife bairro (suburb, neighbourhood,
    quarter, city_district...) and also every part of display_name: addressdetails keeps
    one value per level, so the official bairro is often only in display_name
    (e.g. 'Rua Caburai, UR-07, Varzea' has suburb='UR-07'). City-level values never count.
    """
    alvo = ascii_upper(bairro)
    if not alvo or alvo == "RECIFE":
        return False
    areas = {ascii_upper(v) for k, v in _componentes(componentes_json).items() if k in AREA_KEYS}
    if display_name and not (isinstance(display_name, float) and pd.isna(display_name)):
        areas |= {ascii_upper(p) for p in str(display_name).split(",")[1:]}
    return alvo in areas - {"RECIFE", "PERNAMBUCO", "BRASIL", "REGIAO NORDESTE"}


def _tokens_rua(text: str) -> list[str]:
    return [t for t in re.findall(r"[A-Z]{3,}", ascii_upper(text)) if t not in TOKENS_IGNORADOS]


def rua_confere(rua_consultada: str, componentes_json, display_name=None) -> bool:
    """True if the returned street is the one asked for.

    Nominatim sometimes answers with a different street (Passo 0: 'RUA DA CUSTODIA' ->
    'Rua Rosario de Minas'). At least half of the significant words of the query must
    appear in the returned road name, allowing small spelling differences
    ('TAQUARITINGA' x 'Taquaratinga').
    """
    comp = _componentes(componentes_json)
    devolvida = comp.get("road") or (str(display_name).split(",")[0] if display_name else "")
    pedidas, achadas = _tokens_rua(rua_consultada), _tokens_rua(devolvida)
    if not pedidas or not achadas:
        return False
    iguais = sum(any(SequenceMatcher(None, p, a).ratio() >= 0.8 for a in achadas) for p in pedidas)
    return iguais >= max(1, len(pedidas) / 2)


def load_cache(path: Path = CACHE_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {row["chave"]: row for row in csv.DictReader(f)}


def save_cache(cache: dict[str, dict], path: Path = CACHE_PATH) -> None:
    """Sorted by key for readable git diffs; written to a temp file first so Ctrl+C can't truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CACHE_FIELDS)
        writer.writeheader()
        for key in sorted(cache):
            writer.writerow({k: cache[key].get(k, "") for k in CACHE_FIELDS})
    tmp.replace(path)


class Nominatim:
    def __init__(self, contact: str, session=None, sleep=time.sleep, clock=time.monotonic):
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = (
            f"recife-seguranca-viaria/0.1 (projeto academico CESAR School; contato: {contact})")
        self.sleep, self.clock = sleep, clock
        self._last = None

    def _wait_turn(self) -> None:
        if self._last is not None:
            self.sleep(max(0.0, self._last + MIN_INTERVAL_S - self.clock()))
        self._last = self.clock()

    def search(self, params: dict) -> dict | None:
        """First hit or None. Retries 429/5xx/network errors with backoff; raises on 403."""
        for attempt in range(MAX_RETRIES + 1):
            self._wait_turn()
            try:
                response = self.session.get(URL, params={**FIXED_PARAMS, **params}, timeout=30)
            except (requests.ConnectionError, requests.Timeout):
                if attempt == MAX_RETRIES:
                    raise
                self.sleep(5 * 2 ** attempt)
                continue
            if response.status_code == 403:
                raise NominatimForbidden(response.text[:300])
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == MAX_RETRIES:
                    response.raise_for_status()
                self.sleep(5 * 2 ** attempt)
                continue
            response.raise_for_status()
            hits = response.json()
            return hits[0] if hits else None
        return None


def rua_da_consulta(params: dict) -> str:
    """Street text sent in a query: 'street' minus the house number, or the first part of 'q'."""
    if "street" in params:
        return re.sub(r"^\d+\s+", "", params["street"])
    return params["q"].split(",")[0]


def avaliar(row: dict, params: dict, bairro) -> dict:
    """Cache row + bairro_ok / rua_ok for this sinistro's bairro and the street asked for."""
    if row["nivel"] == "falhou":
        return {**row, "bairro_ok": False, "rua_ok": False}
    return {**row,
            "bairro_ok": bairro_confere(bairro, row["componentes"], row["display_name"]),
            "rua_ok": rua_confere(rua_da_consulta(params), row["componentes"], row["display_name"])}


def _confere(row: dict) -> bool:
    return row["nivel"] != "falhou" and row["bairro_ok"] and row["rua_ok"]


def proxima_consulta(tents: list[tuple[str, dict]], cache: dict[str, dict], bairro) -> tuple[str, dict] | None:
    """Next query this address still needs, or None when the cache already settles it.

    a -> b -> c, stopping at the first hit -- except that a hit from (a)/(b) whose bairro
    or street doesn't match also needs (c): street-only answers are an arbitrary stretch
    of the street, often in another bairro on long or homonymous streets.
    """
    c = next(((n, p) for n, p in tents if n == "c"), None)
    for nome, params in tents:
        row = cache.get(chave(params))
        if row is None:
            return nome, params
        if row["nivel"] == "falhou":
            continue
        if nome != "c" and c is not None and not _confere(avaliar(row, params, bairro)) \
                and chave(c[1]) not in cache:
            return c
        return None
    return None


def resolver(tents: list[tuple[str, dict]], cache: dict[str, dict], bairro) -> dict | None:
    """Offline: the cache row to use (with bairro_ok/rua_ok), a 'falhou' row, or None if nothing cached yet.

    The first hit along a -> b -> c wins, unless it doesn't match and (c) does.
    """
    primeiro, ultimo = None, None
    for nome, params in tents:
        row = cache.get(chave(params))
        if row is None:
            break
        ultimo = avaliar(row, params, bairro)
        if row["nivel"] != "falhou":
            primeiro = ultimo
            break
    if primeiro is None:
        return ultimo
    c = next((p for n, p in tents if n == "c"), None)
    if not _confere(primeiro) and c is not None and primeiro is not None:
        c_row = cache.get(chave(c))
        if c_row is not None and _confere(avaliar(c_row, c, bairro)):
            return avaliar(c_row, c, bairro)
    return primeiro


def pendentes(df: pd.DataFrame) -> list[tuple[str, str | None, str | None, str | None]]:
    """Unique (endereco_norm, endereco, numero, bairro) of rows lacking a confirmed traffic-light coordinate."""
    sem_ok = df["coord_confere"].fillna(False).astype(bool)
    alvo = df.loc[~sem_ok & df["endereco_norm"].notna(), ["endereco_norm", "endereco", "numero", "bairro"]]
    alvo = alvo.assign(numero=alvo["numero"].map(numero_valido))
    return [tuple(None if pd.isna(v) else v for v in row)
            for row in alvo.drop_duplicates().itertuples(index=False)]


def geocode(combos, cache: dict, client: Nominatim | None, limite: int | None = None,
            dry_run: bool = False, cache_path: Path = CACHE_PATH) -> dict:
    """Fill `cache` for the combos still pending. Returns counters."""
    stats = {"combinacoes": len(combos), "ja_resolvidas": 0, "processadas": 0, "consultas": 0}
    desde_salvo = 0
    for endereco_norm, endereco, numero, bairro in combos:
        tents = tentativas(endereco_norm, endereco, numero, bairro)
        if proxima_consulta(tents, cache, bairro) is None:
            stats["ja_resolvidas"] += 1
            continue
        if limite is not None and stats["processadas"] >= limite:
            break
        stats["processadas"] += 1
        while (proxima := proxima_consulta(tents, cache, bairro)) is not None:
            nome, params = proxima
            if dry_run:
                print(f"  consultaria ({nome}): {params}")
                break
            key = chave(params)
            cache[key] = {"chave": key, "tentativa": nome, **parse_hit(client.search(params)),
                          "consultado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            stats["consultas"] += 1
            desde_salvo += 1
            if desde_salvo >= SAVE_EVERY:
                save_cache(cache, cache_path)
                desde_salvo = 0
                print(f"  {stats['consultas']} consultas, {stats['processadas']} enderecos", flush=True)
    if not dry_run:
        save_cache(cache, cache_path)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limite", type=int, help="processa so os N primeiros enderecos pendentes")
    parser.add_argument("--dry-run", action="store_true", help="mostra o que consultaria, sem rede")
    args = parser.parse_args()

    if not BASE_PATH.exists():
        print(f"{BASE_PATH} nao existe -- rode scripts/build_atropelamentos.py antes", file=sys.stderr)
        return 1
    contact = os.environ.get("NOMINATIM_CONTACT", "").strip()
    if not contact and not args.dry_run:
        print("Defina NOMINATIM_CONTACT com um contato (e-mail ou URL) para o User-Agent do Nominatim,\n"
              "exigido pela politica de uso da OSM. Ex.:\n"
              '  export NOMINATIM_CONTACT="seu-email@exemplo.com"\n'
              "  .venv/bin/python scripts/geocode_enderecos.py", file=sys.stderr)
        return 2

    combos = pendentes(pd.read_parquet(BASE_PATH))
    cache = load_cache()
    client = None if args.dry_run else Nominatim(contact)
    print(f"{len(combos)} enderecos sem coordenada de semaforo confirmada; cache com {len(cache)} consultas")
    try:
        stats = geocode(combos, cache, client, limite=args.limite, dry_run=args.dry_run)
    except KeyboardInterrupt:
        save_cache(cache)
        print(f"\ninterrompido -- cache salvo ({len(cache)} consultas). Rode de novo para continuar.")
        return 130
    except NominatimForbidden as err:
        save_cache(cache)
        print(f"\nNominatim respondeu 403 (bloqueado). Parando tudo; cache salvo.\n{err}", file=sys.stderr)
        return 3
    print(stats)
    if not args.dry_run:
        print(f"cache: {CACHE_PATH} ({len(cache)} consultas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
