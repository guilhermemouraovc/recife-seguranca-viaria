"""Adds lat/lon to the cleaned sinistros (output of clean_sinistros.py).

Input:  data/processed/sinistros/sinistros_2015_2024.parquet
        data/raw/cttu/localizacao-dos-semaforos/semáforos_do_recife.csv (fetch_datasets.py --dataset semaforos)
        data/geocode/cache_nominatim.csv (versioned: one row per Nominatim query ever made)
Output: data/processed/sinistros/sinistros_2015_2024_geo.parquet (+ README_geocodificacao.md,
        amostra_conferencia.csv)

Coordinate priority, recorded in `geo_precisao` (and `coord_precisao` alta/media/baixa):
  1. semaforo              num_semaforo joined to the semaforos list AND it matches the sinistro
                           (same bairro, or a street word in localizacao1/2)            -> alta
  2. endereco_numero       Nominatim found the house number, bairro and street match    -> alta
  3. endereco_via          Nominatim found the street (a stretch of it), bairro matches -> media
  4. semaforo_nao_confere  traffic light whose bairro/street don't match                -> baixa
  5. endereco_nao_confere  Nominatim street matches, bairro doesn't                     -> baixa
  6. null                  nothing usable
A Nominatim result on a different street than the one asked for is NEVER used.

Only rows without a matching traffic light are geocoded. Queries per address, in order:
(a) house number + street (only when `numero` is a positive integer), (b) street,
(c) free text with the bairro; (c) is also asked when (a)/(b) land outside the bairro.

Nominatim usage policy (https://operations.osmfoundation.org/policies/nominatim/):
max 1 req/s; User-Agent with a contact read from env NOMINATIM_CONTACT (the script stops
without it); backoff on 429/5xx (3 retries); full stop on 403. Every query, failures
included, is cached and never repeated. Ctrl+C is safe; re-run to resume.
  --offline              only apply the cache (no network, no NOMINATIM_CONTACT needed)
  --dry-run / --limite N show what would be asked / geocode only N addresses
  --importar-cache-json  import the old data/processed/sinistros/geocode_cache.json

Geocodificação (c) colaboradores do OpenStreetMap, ODbL. See docs/11-base-atropelamentos.md.
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
import pyarrow as pa
import pyarrow.parquet as pq
import requests

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed" / "sinistros"
IN_PATH = PROC_DIR / "sinistros_2015_2024.parquet"
OUT_PATH = PROC_DIR / "sinistros_2015_2024_geo.parquet"
CACHE_PATH = ROOT / "data" / "geocode" / "cache_nominatim.csv"
LEGACY_CACHE_PATH = PROC_DIR / "geocode_cache.json"
SEMAFOROS_DIR = ROOT / "data" / "raw" / "cttu" / "localizacao-dos-semaforos"

URL = "https://nominatim.openstreetmap.org/search"
FIXED_PARAMS = {"format": "jsonv2", "addressdetails": 1, "limit": 1, "countrycodes": "br",
                "viewbox": "-35.10,-7.80,-34.80,-8.30", "bounded": 1}
MIN_INTERVAL_S = 1.1
SAVE_EVERY = 25
MAX_RETRIES = 3
SEED = 42

# Recife bounding box; a traffic-light coordinate outside it is discarded.
LAT_RANGE = (-8.30, -7.80)
LON_RANGE = (-35.10, -34.80)

# endereco -> endereco_norm (only the 4 most common street types are abbreviated).
ABREVIACOES = {"AVENIDA": "AV", "RUA": "R", "ESTRADA": "EST", "PRACA": "PCA"}
# Leading abbreviation of endereco_norm -> full word sent to Nominatim. Changing an entry
# changes the cache key of every address that starts with it (it would be queried again).
EXPANSOES = {"AV": "Avenida", "R": "Rua", "EST": "Estrada", "PCA": "Praça", "PRC": "Praça",
             "TV": "Travessa", "TRV": "Travessa", "TRAV": "Travessa", "PTE": "Ponte", "LGO": "Largo",
             "LAD": "Ladeira", "VDO": "Viaduto", "VD": "Viaduto", "COR": "Corredor", "C": "Cais",
             "ROD": "Rodovia", "AL": "Alameda", "PRQ": "Parque"}
TIPOS_POR_EXTENSO = {"RUA", "AVENIDA", "ESTRADA", "PRACA", "TRAVESSA", "PONTE", "LARGO", "LADEIRA",
                     "VIADUTO", "CORREDOR", "CAIS"}
AREA_KEYS = {"suburb", "neighbourhood", "quarter", "city_district", "borough", "hamlet", "village",
             "residential", "city_block", "isolated_dwelling"}
# Street types, articles and title abbreviations: they don't tell two street names apart.
TOKENS_IGNORADOS = {"RUA", "AVENIDA", "ESTRADA", "PRACA", "TRAVESSA", "PONTE", "LARGO", "LADEIRA",
                    "VIADUTO", "CORREDOR", "CAIS", "DAS", "DOS", "GOV", "ENG", "PROF", "DES", "CEL", "GAL",
                    "MAL", "CONS", "DEP", "PRES", "SEN", "VER", "MONS", "CAP", "TEN", "SGT", "DONA"}
# Words too common to say a sinistro street is the traffic light's street.
STOPWORDS_SEMAFORO = {"AV", "R", "EST", "PCA", "DE", "DA", "DO", "DAS", "DOS", "ENG", "DR", "GAL",
                      "GOV", "PTE", "PONTE", "PROX", "FRENTE", "RUA", "AVENIDA"}
CACHE_FIELDS = ["chave", "tentativa", "lat", "lon", "display_name", "osm_type", "osm_id", "class", "type",
                "bairro_retornado", "componentes", "nivel", "consultado_em"]

PRECISAO = {"semaforo": "alta", "endereco_numero": "alta", "endereco_via": "media",
            "semaforo_nao_confere": "baixa", "endereco_nao_confere": "baixa"}

RESSALVAS = [
    "Dados de 2015 so a partir de junho: totais anuais de 2015 estao subestimados.",
    "Sao 'chamados' da CTTU, nao os registros estatisticos dos Relatorios Anuais de Seguranca Viaria; "
    "os numeros podem divergir e nao devem ser rotulados como oficiais do PSVR.",
    "Dados de 2025 sao preliminares: o CSV de 2024 traz 36 sinistros datados de 29-31/12/2025 "
    "(data_fora_do_ano_arquivo=True), provavel erro de digitacao do ano; nao corrigidos.",
    "Queda forte de registros a partir de abr/2020, concentrada em 'SEM VITIMA' e sem recuperacao ate 2024; "
    "a fonte nao explica a causa (hipotese: mudanca no registro de chamados).",
    "Hora vazia em todo o CSV de 2022.",
    "num_semaforo so existe de 2018 em diante: coordenada por semaforo e enviesada para cruzamentos "
    "semaforizados e quase inexistente em 2015-2017.",
    "Coordenada de semaforo e a do semaforo informado no chamado, nao a do ponto exato do sinistro.",
    "'endereco_via' e um ponto qualquer da rua dentro do bairro, nao o local do sinistro; em vias longas o "
    "erro pode passar de 1 km, e todos os sinistros da mesma rua+bairro caem no mesmo ponto ('pilhas'). "
    "Use coord_precisao para filtrar.",
    "Geocodificacao (c) colaboradores do OpenStreetMap, ODbL.",
]


class NominatimForbidden(RuntimeError):
    """HTTP 403: the service blocked us -- never keep going after this."""


def _missing(value) -> bool:
    return value is None or value is pd.NA or (isinstance(value, float) and pd.isna(value))


def ascii_upper(value) -> str:
    """Uppercase, accent-free, spaces collapsed; '' for missing."""
    if _missing(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text.upper()).strip()


def normalize_endereco(value) -> str | None:
    """'Av. Eng. José Estelita,' -> 'AV ENG JOSE ESTELITA'; None if nothing is left."""
    tokens = re.sub(r"[^A-Z0-9]+", " ", ascii_upper(value)).split()
    return " ".join(ABREVIACOES.get(t, t) for t in tokens) or None


def normalize_num_semaforo(value) -> str | None:
    """'037', '37', '37,0', '37.0', 37 -> '37'; empty, zero or non-numeric ('S/N', '37,5') -> None."""
    if _missing(value):
        return None
    match = re.fullmatch(r"0*(\d+)(?:[.,]0+)?", str(value).strip())
    if not match or match.group(1) == "0":
        return None
    return match.group(1)


# --- Nominatim queries -------------------------------------------------------------------

def expandir_rua(endereco_norm: str, endereco: str | None = None) -> str:
    """'AV CAXANGA' -> 'Avenida CAXANGA'.

    The original endereco is used instead when it already spells the street type out
    and has no dotted abbreviations (e.g. 'RUA DIADEMA').
    """
    original = re.sub(r"[^\w\s]", " ", endereco or "").split()
    if original and ascii_upper(original[0]) in TIPOS_POR_EXTENSO and "." not in (endereco or ""):
        return " ".join(original)
    first, _, rest = endereco_norm.partition(" ")
    return f"{EXPANSOES.get(first, first)} {rest}".strip()


def numero_valido(numero) -> str | None:
    """Only plain positive integers are sent as house numbers ('XX', 'S/N', '312A' are not)."""
    text = "" if _missing(numero) else str(numero).strip()
    return text if re.fullmatch(r"[1-9]\d*", text) else None


def tentativas(endereco_norm: str, endereco: str | None, numero, bairro) -> list[tuple[str, dict]]:
    """Ordered queries for one address: (a) number + street, (b) street, (c) free text with bairro."""
    rua = expandir_rua(endereco_norm, endereco)
    out = []
    num = numero_valido(numero)
    if num:
        out.append(("a", {"street": f"{num} {rua}", "city": "Recife", "state": "Pernambuco"}))
    out.append(("b", {"street": rua, "city": "Recife", "state": "Pernambuco"}))
    if not _missing(bairro) and bairro:
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
        nivel = "outro"  # a place that is neither a numbered address nor a street (e.g. a suburb)
    return {
        "lat": hit["lat"], "lon": hit["lon"], "display_name": hit.get("display_name"),
        "osm_type": hit.get("osm_type"), "osm_id": hit.get("osm_id"),
        "class": hit.get("category"), "type": hit.get("type"),
        "bairro_retornado": addr.get("suburb") or addr.get("neighbourhood"),
        "componentes": json.dumps(addr, ensure_ascii=False), "nivel": nivel,
    }


def _componentes(componentes_json) -> dict:
    if _missing(componentes_json) or not componentes_json:
        return {}
    return json.loads(componentes_json)


def bairro_confere(bairro, componentes_json, display_name=None) -> bool:
    """True if the sinistro bairro equals any sub-city area of the returned address.

    Checks every area level OSM may use (suburb, neighbourhood, quarter, city_district...)
    and every part of display_name: addressdetails keeps one value per level, so the
    official bairro is often only in display_name ('Rua Caburai, UR-07, Varzea').
    City-level values never count.
    """
    alvo = ascii_upper(bairro)
    if not alvo or alvo == "RECIFE":
        return False
    areas = {ascii_upper(v) for k, v in _componentes(componentes_json).items() if k in AREA_KEYS}
    if not _missing(display_name) and display_name:
        areas |= {ascii_upper(p) for p in str(display_name).split(",")[1:]}
    return alvo in areas - {"RECIFE", "PERNAMBUCO", "BRASIL", "REGIAO NORDESTE"}


def _tokens_rua(text: str) -> list[str]:
    return [t for t in re.findall(r"[A-Z]{3,}", ascii_upper(text)) if t not in TOKENS_IGNORADOS]


def rua_confere(rua_consultada: str, componentes_json, display_name=None) -> bool:
    """True if the returned street is the one asked for.

    At least half of the significant words of the query must appear in the returned road
    name, allowing small spelling differences ('TAQUARITINGA' x 'Taquaratinga').
    Nominatim sometimes answers another street ('RUA DA CUSTODIA' -> 'Rua Rosario de Minas').
    """
    comp = _componentes(componentes_json)
    devolvida = comp.get("road") or (str(display_name).split(",")[0] if display_name else "")
    pedidas, achadas = _tokens_rua(rua_consultada), _tokens_rua(devolvida)
    if not pedidas or not achadas:
        return False
    iguais = sum(any(SequenceMatcher(None, p, a).ratio() >= 0.8 for a in achadas) for p in pedidas)
    return iguais >= max(1, len(pedidas) / 2)


# --- cache -------------------------------------------------------------------------------

def load_cache(path: Path = CACHE_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {row["chave"]: row for row in csv.DictReader(f)}


def save_cache(cache: dict[str, dict], path: Path = CACHE_PATH) -> None:
    """Sorted by key for readable git diffs; temp file first so Ctrl+C can't truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CACHE_FIELDS)
        writer.writeheader()
        for key in sorted(cache):
            writer.writerow({k: cache[key].get(k, "") for k in CACHE_FIELDS})
    tmp.replace(path)


def importar_cache_json(legacy: dict, cache: dict[str, dict]) -> int:
    """Converts the old geocode_cache.json ("ENDERECO|BAIRRO" -> hit | None) into cache rows.

    The old script asked q="<rua>, <bairro>, Recife, PE" ("via_bairro") and, failing that,
    q="<rua>, Recife, PE" ("via"). They are stored as the equivalent queries (c) and (b).
    The old cache has no addressdetails, so nivel is 'via' and the bairro/street checks use
    display_name only. A None (both failed) becomes 'falhou' for (b) and (c). Existing
    rows are never overwritten. Returns how many rows were added.
    """
    added = 0
    for key, hit in legacy.items():
        endereco, _, bairro = key.partition("|")
        norm = normalize_endereco(endereco)
        if not norm or not bairro:
            continue
        tents = dict(tentativas(norm, endereco, None, bairro))
        if hit is None:
            novos = {"b": {"nivel": "falhou"}, "c": {"nivel": "falhou"}}
        else:
            nome = "c" if hit.get("precisao") == "via_bairro" else "b"
            novos = {nome: {"lat": hit["lat"], "lon": hit["lon"], "display_name": hit.get("display_name"),
                            "nivel": "via"}}
            if nome == "b":
                novos["c"] = {"nivel": "falhou"}  # the old script asked with the bairro first
        for nome, row in novos.items():
            k = chave(tents[nome])
            if k not in cache:
                cache[k] = {"chave": k, "tentativa": nome, **row,
                            "consultado_em": "importado de geocode_cache.json"}
                added += 1
    return added


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
            "bairro_ok": bairro_confere(bairro, row.get("componentes"), row.get("display_name")),
            "rua_ok": rua_confere(rua_da_consulta(params), row.get("componentes"), row.get("display_name"))}


def _confere(row: dict) -> bool:
    return row["nivel"] != "falhou" and row["bairro_ok"] and row["rua_ok"]


def proxima_consulta(tents: list[tuple[str, dict]], cache: dict[str, dict], bairro) -> tuple[str, dict] | None:
    """Next query this address still needs, or None when the cache already settles it.

    a -> b -> c, stopping at the first hit -- except that a hit from (a)/(b) whose bairro
    or street doesn't match also needs (c): a street-only answer is an arbitrary stretch
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
    """Offline: the cache row to use (with bairro_ok/rua_ok), a 'falhou' row, or None if nothing cached.

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
    if not _confere(primeiro) and c is not None:
        c_row = cache.get(chave(c))
        if c_row is not None and _confere(avaliar(c_row, c, bairro)):
            return avaliar(c_row, c, bairro)
    return primeiro


def geocode(combos, cache: dict, client: Nominatim | None, limite: int | None = None,
            dry_run: bool = False, cache_path: Path = CACHE_PATH) -> dict:
    """Fill `cache` for the (endereco_norm, endereco, numero, bairro) combos still pending."""
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


# --- traffic lights ----------------------------------------------------------------------

def street_tokens(text) -> set[str]:
    return {t for t in re.findall(r"[A-Z]{3,}", ascii_upper(text)) if t not in STOPWORDS_SEMAFORO}


def load_semaforos() -> tuple[pd.DataFrame | None, list[dict]]:
    """Traffic lights keyed by semaforo_norm with validated lat/lon, plus a log of fixes."""
    csvs = sorted(SEMAFOROS_DIR.glob("*recife.csv")) or sorted(SEMAFOROS_DIR.glob("*.csv"))
    if not csvs:
        print("semaforos nao baixados -- rode fetch_datasets.py --dataset semaforos (pulando)")
        return None, []
    sem = pd.read_csv(csvs[0], sep=";", dtype=str, keep_default_na=False)
    sem.columns = sem.columns.str.strip().str.lower()
    ajustes = []
    for col in ("latitude", "longitude"):
        raw = sem[col].str.strip()
        # Observed once (semaforo 693: '-8.060979,'): stray trailing comma. Strip it and log.
        for _, row in sem[raw.str.endswith(",")].iterrows():
            ajustes.append({"semaforo": row["semaforo"], "coluna": col, "valor_original": row[col],
                            "ajuste": "virgula final removida"})
        sem[col] = pd.to_numeric(raw.str.rstrip(",").str.replace(",", ".", regex=False), errors="coerce")
    valid = sem["latitude"].between(*LAT_RANGE) & sem["longitude"].between(*LON_RANGE)
    for _, row in sem[~valid].iterrows():
        ajustes.append({"semaforo": row["semaforo"], "coluna": "latitude/longitude",
                        "valor_original": f"{row['latitude']}, {row['longitude']}",
                        "ajuste": "fora do Recife ou invalida: coordenada descartada"})
    sem = sem[valid].copy()
    sem["semaforo_norm"] = sem["semaforo"].map(normalize_num_semaforo)
    dup = sem["semaforo_norm"].dropna().duplicated()
    if dup.any():
        raise ValueError(f"semaforo duplicado apos normalizar: {sem['semaforo_norm'].dropna()[dup].tolist()}")
    sem["sem_bairro"] = sem["bairro"].map(ascii_upper)
    sem["sem_tokens"] = (sem["localizacao1"] + " " + sem["localizacao2"]).map(street_tokens)
    keep = ["semaforo_norm", "latitude", "longitude", "sem_bairro", "sem_tokens"]
    return sem.loc[sem["semaforo_norm"].notna(), keep], ajustes


def semaforo_confere(bairro, endereco, sem_bairro: str, sem_tokens: set[str]) -> bool:
    """The traffic light plausibly is the sinistro's place: same bairro, or a street word in common."""
    return (bool(ascii_upper(bairro)) and ascii_upper(bairro) == sem_bairro) or bool(street_tokens(endereco) & sem_tokens)


# --- final coordinate --------------------------------------------------------------------

def coordenada_final(sem: tuple | None, sem_confere, geo: dict | None) -> tuple:
    """(lat, lon, geo_precisao) by the priority in the module docstring."""
    usavel = geo is not None and geo["nivel"] != "falhou" and geo["rua_ok"]
    geo_coord = (float(geo["lat"]), float(geo["lon"])) if usavel else None
    if sem is not None and sem_confere is True:
        return (*sem, "semaforo")
    if usavel and geo["bairro_ok"] and geo["nivel"] == "numero":
        return (*geo_coord, "endereco_numero")
    if usavel and geo["bairro_ok"] and geo["nivel"] == "via":
        return (*geo_coord, "endereco_via")
    if sem is not None:
        return (*sem, "semaforo_nao_confere")
    if usavel:
        return (*geo_coord, "endereco_nao_confere")
    return (None, None, None)


def preparar(df: pd.DataFrame, semaforos: pd.DataFrame | None) -> pd.DataFrame:
    """Adds endereco_norm, num_semaforo_norm, lat/lon_semaforo, coord_confere (no network)."""
    df = df.copy()
    df["endereco_norm"] = df["endereco"].map(normalize_endereco)
    df["num_semaforo_norm"] = df["num_semaforo"].map(normalize_num_semaforo)
    if semaforos is None:
        df["lat_semaforo"] = df["lon_semaforo"] = float("nan")
        df["coord_confere"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
        return df
    m = df[["num_semaforo_norm"]].merge(semaforos, how="left", left_on="num_semaforo_norm",
                                        right_on="semaforo_norm")
    m.index = df.index
    df["lat_semaforo"], df["lon_semaforo"] = m["latitude"], m["longitude"]
    confere = [semaforo_confere(b, e, sb, st) if isinstance(st, set) else None
               for b, e, sb, st in zip(df["bairro"], df["endereco"], m["sem_bairro"], m["sem_tokens"])]
    df["coord_confere"] = pd.Series(confere, index=df.index, dtype="boolean")
    return df


def pendentes(df: pd.DataFrame) -> list[tuple]:
    """Unique (endereco_norm, endereco, numero, bairro) of rows lacking a matching traffic light."""
    sem_ok = df["coord_confere"].fillna(False).astype(bool)
    alvo = df.loc[~sem_ok & df["endereco_norm"].notna(), ["endereco_norm", "endereco", "numero", "bairro"]]
    alvo = alvo.assign(numero=alvo["numero"].map(numero_valido))
    return [tuple(None if _missing(v) else v for v in row) for row in alvo.drop_duplicates().itertuples(index=False)]


def aplicar(df: pd.DataFrame, cache: dict[str, dict]) -> tuple[pd.DataFrame, dict]:
    """Sets lat/lon/geo_precisao/coord_precisao and audit columns from the cache (offline)."""
    resolvidos, situacao = {}, []
    linhas = []
    for norm, end, num, bairro, ok in zip(df["endereco_norm"], df["endereco"], df["numero"], df["bairro"],
                                          df["coord_confere"].fillna(False).astype(bool)):
        if _missing(norm):
            linhas.append(None)
            situacao.append("sem_endereco")
            continue
        k = (norm, end, numero_valido(num), None if _missing(bairro) else bairro)
        if k not in resolvidos:
            tents = tentativas(*k)
            resolvidos[k] = (resolver(tents, cache, k[3]), proxima_consulta(tents, cache, k[3]) is not None)
        row, falta = resolvidos[k]
        linhas.append(row)
        if row is None:
            situacao.append("nao_consultado_semaforo_ok" if ok else "pendente")
        elif row["nivel"] == "falhou":
            situacao.append("falhou")
        elif not ok and falta:
            situacao.append("encontrado_falta_tentativa_c")
        else:
            situacao.append("encontrado")

    finais = [coordenada_final(None if pd.isna(la) else (la, lo), None if _missing(c) else bool(c), g)
              for la, lo, c, g in zip(df["lat_semaforo"], df["lon_semaforo"], df["coord_confere"], linhas)]
    df = df.copy()
    df["lat"] = pd.array([f[0] for f in finais], dtype="Float64")
    df["lon"] = pd.array([f[1] for f in finais], dtype="Float64")
    df["geo_precisao"] = pd.array([f[2] for f in finais], dtype="string")
    df["coord_precisao"] = df["geo_precisao"].map(PRECISAO).astype("string")
    usa_geo = df["geo_precisao"].str.startswith("endereco_").fillna(False)
    achado = [g is not None and g["nivel"] != "falhou" for g in linhas]
    df["geo_display_name"] = [g["display_name"] if u else None for g, u in zip(linhas, usa_geo)]
    df["geo_nivel"] = [g["nivel"] if g is not None else None for g in linhas]
    df["geo_tentativa"] = [g["tentativa"] if a else None for g, a in zip(linhas, achado)]
    df["geo_bairro_confere"] = pd.array([g["bairro_ok"] if a else None for g, a in zip(linhas, achado)], dtype="boolean")
    df["geo_rua_confere"] = pd.array([g["rua_ok"] if a else None for g, a in zip(linhas, achado)], dtype="boolean")
    situacao = pd.Series(situacao, index=df.index)
    stats = {
        "consultas_no_cache": len(cache),
        "situacao_por_linha": situacao.value_counts().to_dict(),
        "geocode_descartado_rua_diferente": int((pd.Series(achado, index=df.index)
                                                 & ~df["geo_rua_confere"].fillna(True)).sum()),
        "top20_enderecos_que_falharam": df.loc[situacao == "falhou", "endereco_norm"].value_counts().head(20).to_dict(),
    }
    return df, stats


# --- outputs -----------------------------------------------------------------------------

def _pct(s: pd.Series) -> float:
    return round(float(s.mean()) * 100, 1)


def readme(df: pd.DataFrame, stats: dict, ajustes: list[dict]) -> str:
    por_ano = pd.DataFrame({
        "sinistros": df.groupby("ano_arquivo").size(),
        "%coord_so_semaforo": df.groupby("ano_arquivo")["lat_semaforo"].apply(lambda s: _pct(s.notna())),
        "%coord": df.groupby("ano_arquivo")["lat"].apply(lambda s: _pct(s.notna())),
        "%alta_ou_media": df.groupby("ano_arquivo")["coord_precisao"].apply(lambda s: _pct(s.isin(["alta", "media"]))),
    })
    atrop = df[df["atropelamento"]]
    pontos = df.loc[df["lat"].notna(), ["lat", "lon"]].drop_duplicates()
    ressalvas = "\n".join(f"{i}. {r}" for i, r in enumerate(RESSALVAS, 1))
    return f"""# Sinistros geocodificados (processado)

Gerado por `scripts/geocode_sinistros.py` a partir de `sinistros_2015_2024.parquet` e do cache
versionado `data/geocode/cache_nominatim.csv`. Método e limitações: `docs/11-base-atropelamentos.md`.
Geocodificação © colaboradores do OpenStreetMap, ODbL.

## Ressalvas (não remover)

{ressalvas}

## Cobertura por ano (todos os sinistros)

```
{por_ano.to_string()}
```

Atropelamentos: {len(atrop)} linhas, {_pct(atrop['lat'].notna())}% com coordenada,
{_pct(atrop['coord_precisao'].isin(['alta', 'media']))}% com precisão alta ou média.
Pontos distintos: {len(pontos)} para {int(df['lat'].notna().sum())} linhas com coordenada ("pilhas").

## geo_precisao

```
{df['geo_precisao'].value_counts(dropna=False).to_string()}
```

## Geocodificação por linha

```
{json.dumps(stats, ensure_ascii=False, indent=2)}
```

## Ajustes no dataset de semáforos

```
{json.dumps(ajustes, ensure_ascii=False, indent=2)}
```
"""


def write_parquet(df: pd.DataFrame, path: Path = OUT_PATH) -> None:
    table = pa.Table.from_pandas(df, preserve_index=False)
    meta = dict(table.schema.metadata or {})
    meta[b"ressalvas"] = json.dumps(RESSALVAS, ensure_ascii=False).encode()
    meta[b"documentacao"] = b"docs/11-base-atropelamentos.md"
    pq.write_table(table.replace_schema_metadata(meta), path)


def write_amostra(df: pd.DataFrame, n: int = 30) -> None:
    """Random sample of atropelamentos with a coordinate + OSM link, to check by hand."""
    com = df[df["lat"].notna() & df["atropelamento"]]
    amostra = com.sample(min(n, len(com)), random_state=SEED)[
        ["data", "bairro", "endereco", "numero", "num_semaforo_norm", "geo_precisao", "coord_precisao",
         "geo_display_name", "lat", "lon"]].copy()
    amostra["link_osm"] = [f"https://www.openstreetmap.org/?mlat={la}&mlon={lo}#map=18/{la}/{lo}"
                           for la, lo in zip(amostra["lat"], amostra["lon"])]
    amostra["conferido_ok"] = ""
    amostra["observacao"] = ""
    amostra.to_csv(PROC_DIR / "amostra_conferencia.csv", index=False, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="so aplica o cache, sem rede")
    parser.add_argument("--dry-run", action="store_true", help="mostra o que consultaria, sem rede")
    parser.add_argument("--limite", type=int, help="geocodifica so os N primeiros enderecos pendentes")
    parser.add_argument("--importar-cache-json", nargs="?", const=str(LEGACY_CACHE_PATH), metavar="PATH",
                        help="importa o geocode_cache.json antigo para o cache versionado")
    args = parser.parse_args()

    if not IN_PATH.exists():
        print(f"{IN_PATH} nao existe -- rode scripts/clean_sinistros.py antes", file=sys.stderr)
        return 1
    contact = os.environ.get("NOMINATIM_CONTACT", "").strip()
    online = not args.offline and not args.dry_run
    if online and not contact:
        print("Defina NOMINATIM_CONTACT com um contato (e-mail ou URL) para o User-Agent do Nominatim,\n"
              "exigido pela politica de uso da OSM. Ex.:\n"
              '  export NOMINATIM_CONTACT="seu-email@exemplo.com"\n'
              "Ou rode com --offline para so aplicar o cache.", file=sys.stderr)
        return 2

    cache = load_cache()
    if args.importar_cache_json:
        added = importar_cache_json(json.loads(Path(args.importar_cache_json).read_text()), cache)
        save_cache(cache)
        print(f"importadas {added} consultas de {args.importar_cache_json}")

    semaforos, ajustes = load_semaforos()
    df = preparar(pd.read_parquet(IN_PATH), semaforos)
    if not args.offline:
        combos = pendentes(df)
        print(f"{len(combos)} enderecos sem semaforo confirmado; cache com {len(cache)} consultas")
        try:
            print(geocode(combos, cache, Nominatim(contact) if online else None,
                          limite=args.limite, dry_run=args.dry_run))
        except KeyboardInterrupt:
            save_cache(cache)
            print(f"\ninterrompido -- cache salvo ({len(cache)} consultas). Rode de novo para continuar.")
            return 130
        except NominatimForbidden as err:
            save_cache(cache)
            print(f"\nNominatim respondeu 403 (bloqueado). Parando tudo; cache salvo.\n{err}", file=sys.stderr)
            return 3
        if args.dry_run:
            return 0

    df, stats = aplicar(df, cache)
    write_parquet(df)
    (PROC_DIR / "README_geocodificacao.md").write_text(readme(df, stats, ajustes), encoding="utf-8")
    write_amostra(df)
    print(df["geo_precisao"].value_counts(dropna=False).to_string())
    print(json.dumps(stats["situacao_por_linha"], ensure_ascii=False))
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
