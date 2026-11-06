"""Builds data/processed/atropelamentos.parquet: one row per pedestrian-collision sinistro (M1).

Inputs (download first with scripts/fetch_datasets.py):
  data/raw/cttu/acidentes-de-transito-com-e-sem-vitimas/*.csv  (sinistros 2015-2024)
  data/raw/cttu/localizacao-dos-semaforos/*.csv               (resource "Semaforos do Recife")
  data/geocode/cache_nominatim.csv                            (optional, filled by geocode_enderecos.py)

Outputs:
  data/processed/atropelamentos.parquet
  data/processed/atropelamentos_qualidade.json
  data/processed/amostra_conferencia.csv

Runs offline. Coordinates come from joining num_semaforo to the traffic-light
list and from the Nominatim cache (read only -- this script never queries it),
chosen by the priority in coordenada_final(). Rows without a coordinate are
kept with lat/lon null.
Every source anomaly handled here is counted in the quality report and
described in docs/11-base-atropelamentos.md (docs/06: document, don't hide).
"""
import json
import re
import unicodedata

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import geocode_enderecos as geocode
import sinistros

ROOT = sinistros.ROOT
SEMAFOROS_DIR = ROOT / "data" / "raw" / "cttu" / "localizacao-dos-semaforos"
OUT_DIR = ROOT / "data" / "processed"
OUT_PARQUET = OUT_DIR / "atropelamentos.parquet"
OUT_QUALIDADE = OUT_DIR / "atropelamentos_qualidade.json"

# Recife bounding box; a coordinate outside it is treated as invalid.
LAT_RANGE = (-8.30, -7.80)
LON_RANGE = (-35.10, -34.80)

ABREVIACOES = {"AVENIDA": "AV", "RUA": "R", "ESTRADA": "EST", "PRACA": "PCA"}
# Words too common to say two street names are the same street (coord_confere).
STOPWORDS = {"AV", "R", "EST", "PCA", "DE", "DA", "DO", "DAS", "DOS", "ENG", "DR", "GAL",
             "GOV", "PTE", "PONTE", "PROX", "FRENTE", "RUA", "AVENIDA"}

TEXT_COLS = ["protocolo", "data", "hora", "natureza", "tipo", "bairro", "endereco", "numero",
             "bairro_cruzamento", "num_semaforo"]
COUNT_COLS = ["pedestre", "moto", "ciclista", "auto", "onibus", "caminhao", "vitimas", "vitimasfatais"]

OUTPUT_COLS = [
    "protocolo", "data", "hora", "datahora", "ano", "mes", "dia_semana", "faixa_horaria",
    "natureza", "tipo", "bairro", "endereco", "numero", "bairro_cruzamento",
    "endereco_norm", "num_semaforo_norm", *[c for c in COUNT_COLS],
    "gravidade", "lat", "lon", "coord_fonte", "coord_precisao", "geo_display_name",
    "lat_semaforo", "lon_semaforo", "coord_confere",
    "geo_nivel", "geo_tentativa", "geo_bairro_confere", "geo_rua_confere",
    "local_id", "criterio_atropelamento",
]

# coord_fonte -> coord_precisao (docs/11, "Geocodificacao").
PRECISAO = {"semaforo": "alta", "endereco_numero": "alta", "endereco_via": "media",
            "semaforo_nao_confere": "baixa", "endereco_nao_confere": "baixa"}
OUT_AMOSTRA = OUT_DIR / "amostra_conferencia.csv"
SEED = 42

RESSALVAS = [
    "Dados de 2015 so a partir de junho: totais anuais de 2015 estao subestimados.",
    "Sao 'chamados' da CTTU, nao os registros estatisticos dos Relatorios Anuais de Seguranca Viaria; "
    "os numeros podem divergir e nao devem ser rotulados como oficiais do PSVR.",
    "Dados de 2025, quando presentes, sao preliminares (classificacao do proprio PSVR).",
    "O CSV de 2015 nao tem a coluna vitimasfatais: valor null (desconhecido), nunca zero.",
    "Queda forte de registros a partir de abr/2020, concentrada em 'SEM VITIMA' e sem recuperacao ate 2024; "
    "a fonte nao explica a causa (hipotese: mudanca no registro de chamados). Atropelamentos variam bem menos.",
    "Hora vazia em todo o CSV de 2022: hora/datahora/faixa_horaria null nesse ano.",
    "num_semaforo so existe de 2018 em diante: 2015-2017 nao tem coordenada; cobertura de coordenada "
    "e baixa e enviesada para cruzamentos semaforizados.",
    "Coordenada de semaforo e a do semaforo informado no chamado, nao a do ponto exato do sinistro; "
    "coord_confere=False marca vinculos em que nem bairro nem rua batem com o semaforo.",
    "Coordenadas 'endereco_*' vem de geocodificacao (Nominatim/OpenStreetMap): 'endereco_via' e um ponto "
    "qualquer da rua dentro do bairro, nao o local do sinistro; em vias longas o erro pode passar de 1 km. "
    "Use coord_precisao para filtrar.",
    "Geocodificacao (c) colaboradores do OpenStreetMap, ODbL.",
]


def ascii_upper(value) -> str:
    """Uppercase, accent-free, stripped; '' for missing."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return text.upper().strip()


def normalize_endereco(value) -> str | None:
    """'Av. Eng. José Estelita,' -> 'AV ENG JOSE ESTELITA'; None if nothing is left."""
    tokens = re.sub(r"[^A-Z0-9]+", " ", ascii_upper(value)).split()
    tokens = [ABREVIACOES.get(t, t) for t in tokens]
    return " ".join(tokens) or None


def normalize_num_semaforo(value) -> str | None:
    """'037', '37', '37,0', '37.0' -> '37'; empty, zero or non-numeric (e.g. 'S/N') -> None."""
    match = re.fullmatch(r"0*(\d+)(?:[.,]0+)?", str(value).strip()) if value is not None else None
    if not match or match.group(1) == "0":
        return None
    return match.group(1)


def slug(value) -> str:
    return re.sub(r"[^a-z0-9]+", "-", ascii_upper(value).lower()).strip("-") or "desconhecido"


def parse_numbers(series: pd.Series) -> tuple[pd.Series, int]:
    """'1,0' -> 1.0; blank -> NaN (unknown, not zero). Also returns how many non-blank values failed."""
    text = series.fillna("").astype(str).str.strip()
    parsed = pd.to_numeric(text.str.replace(",", ".", regex=False), errors="coerce")
    return parsed, int((parsed.isna() & (text != "")).sum())


def criterio_atropelamento(tipo: pd.Series, pedestre: pd.Series) -> pd.Series:
    """'tipo+pedestre' | 'tipo' | 'pedestre' | None.

    tipo matches any ATROPELAMENTO variant except animal ones
    (ATROPELAMENTO, ATROPELAMENTO DE PESSOA; not ATROPELAMENTO [DE] ANIMAL).
    pedestre is a count (> 0 means a pedestrian was involved).
    """
    tipo_norm = tipo.map(ascii_upper)
    por_tipo = tipo_norm.str.contains("ATROPELAMENTO") & ~tipo_norm.str.contains("ANIMAL")
    por_pedestre = pd.to_numeric(pedestre, errors="coerce").fillna(0) > 0
    criterio = [
        "tipo+pedestre" if t and p else "tipo" if t else "pedestre" if p else None
        for t, p in zip(por_tipo, por_pedestre)
    ]
    return pd.Series(criterio, index=tipo.index, dtype="object")


def gravidade(natureza: pd.Series, vitimas: pd.Series, vitimasfatais: pd.Series) -> pd.Series:
    """fatal > natureza (COM/SEM VITIMA) > vitimas count > desconhecida.

    The source sometimes contradicts itself (e.g. 'VITIMA FATAL' with vitimas=0);
    natureza wins over the counts except that any vitimasfatais > 0 is fatal.
    """
    nat = natureza.map(ascii_upper)
    out = pd.Series("desconhecida", index=natureza.index, dtype="object")
    out[vitimas > 0] = "com_vitima"
    out[nat == "SEM VITIMA"] = "sem_vitima"
    out[nat == "COM VITIMA"] = "com_vitima"
    out[(nat == "VITIMA FATAL") | (vitimasfatais > 0)] = "fatal"
    return out


def street_tokens(text) -> set[str]:
    return {t for t in re.findall(r"[A-Z]{3,}", ascii_upper(text)) if t not in STOPWORDS}


def load_semaforos() -> tuple[pd.DataFrame, list[dict]]:
    """Traffic lights keyed by semaforo_norm, with validated lat/lon; plus a log of fixes."""
    csv_path = next(SEMAFOROS_DIR.glob("*.csv"))
    sem = pd.read_csv(csv_path, sep=";", dtype=str, keep_default_na=False)
    sem.columns = sem.columns.str.strip().str.lower()
    ajustes = []
    for col in ("latitude", "longitude"):
        raw = sem[col].str.strip()
        # Observed once (semaforo 693: '-8.060979,'): stray trailing comma. Strip it and log.
        trailing = raw.str.endswith(",")
        for _, row in sem[trailing].iterrows():
            ajustes.append({"semaforo": row["semaforo"], "coluna": col, "valor_original": row[col],
                            "ajuste": "virgula final removida"})
        sem[col] = pd.to_numeric(raw.str.rstrip(",").str.replace(",", ".", regex=False), errors="coerce")
    valid = sem["latitude"].between(*LAT_RANGE) & sem["longitude"].between(*LON_RANGE)
    for _, row in sem[~valid].iterrows():
        ajustes.append({"semaforo": row["semaforo"], "coluna": "latitude/longitude",
                        "valor_original": f"{row['latitude']}, {row['longitude']}",
                        "ajuste": "fora do Recife ou invalida: coordenada descartada"})
    sem.loc[~valid, ["latitude", "longitude"]] = None
    sem["semaforo_norm"] = sem["semaforo"].map(normalize_num_semaforo)
    dup = sem["semaforo_norm"].dropna().duplicated()
    if dup.any():
        raise ValueError(f"semaforo duplicado apos normalizar: {sem['semaforo_norm'].dropna()[dup].tolist()}")
    sem["sem_bairro"] = sem["bairro"].map(ascii_upper)
    sem["sem_tokens"] = (sem["localizacao1"] + " " + sem["localizacao2"]).map(street_tokens)
    keep = ["semaforo_norm", "latitude", "longitude", "sem_bairro", "sem_tokens"]
    return sem.loc[sem["semaforo_norm"].notna(), keep], ajustes


def load_sinistros() -> tuple[pd.DataFrame, dict]:
    """All years, raw text columns aligned (missing column -> NA), plus per-file stats."""
    frames, stats = [], {"linhas_por_arquivo": {}, "colunas_ausentes": {}}
    for year, df in sinistros.read_all(dtype=str, keep_default_na=False):
        df = df.apply(lambda col: col.str.strip())
        ausentes = [c for c in TEXT_COLS + COUNT_COLS if c not in df.columns]
        stats["colunas_ausentes"][str(year)] = ausentes
        stats["linhas_por_arquivo"][str(year)] = len(df)
        df = df.reindex(columns=TEXT_COLS + COUNT_COLS)
        df["ano_arquivo"] = year
        frames.append(df)
    if not frames:
        raise SystemExit(f"nenhum CSV em {sinistros.SINISTROS_DIR} -- rode scripts/fetch_datasets.py antes")
    return pd.concat(frames, ignore_index=True), stats


def coordenada_final(sem: tuple | None, sem_confere, geo: dict | None) -> tuple:
    """(lat, lon, coord_fonte) by the M1b priority.

    sem: (lat, lon) of the traffic light or None. sem_confere: coord_confere.
    geo: resolved cache row with 'lat', 'lon', 'nivel', 'bairro_ok', 'rua_ok', or None.
      1. semaforo conferindo            -> semaforo
      2. geocode numero + bairro confere -> endereco_numero
      3. geocode via + bairro confere    -> endereco_via
      4. semaforo nao conferindo        -> semaforo_nao_confere
      5. geocode sem bairro conferindo  -> endereco_nao_confere (also 'outro' places)
      6. nada                           -> (None, None, None)
    A geocode hit on a different street (rua_ok False) is never used.
    """
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


def add_coordenada_final(df: pd.DataFrame) -> dict:
    """Reads the Nominatim cache (offline) and sets lat/lon/coord_fonte/coord_precisao in place."""
    cache = geocode.load_cache()
    if not cache:
        print(f"aviso: {geocode.CACHE_PATH} vazio ou ausente -- so coordenadas de semaforo "
              "(rode scripts/geocode_enderecos.py)")
    resolvidos, situacao = [], []
    sem_ok = df["coord_confere"].fillna(False).astype(bool)
    for norm, end, num, bairro, ok in zip(df["endereco_norm"], df["endereco"], df["numero"], df["bairro"], sem_ok):
        if norm is None or pd.isna(norm):
            resolvidos.append(None)
            situacao.append("sem_endereco")
            continue
        tents = geocode.tentativas(norm, end, num, bairro)
        row = geocode.resolver(tents, cache, bairro)
        if row is None:
            # geocode_enderecos.py skips rows with a confirmed traffic light on purpose.
            situacao.append("nao_consultado_semaforo_ok" if ok else "pendente")
        elif row["nivel"] == "falhou":
            situacao.append("falhou")
        elif not ok and geocode.proxima_consulta(tents, cache, bairro) is not None:
            situacao.append("encontrado_falta_tentativa_c")
        else:
            situacao.append("encontrado")
        resolvidos.append(row)

    finais = [
        coordenada_final(None if pd.isna(la) else (la, lo), None if pd.isna(c) else bool(c), g)
        for la, lo, c, g in zip(df["lat_semaforo"], df["lon_semaforo"], df["coord_confere"], resolvidos)
    ]
    df["lat"] = [f[0] for f in finais]
    df["lon"] = [f[1] for f in finais]
    df["coord_fonte"] = [f[2] for f in finais]
    df["coord_precisao"] = df["coord_fonte"].map(PRECISAO)
    usa_geo = df["coord_fonte"].str.startswith("endereco_", na=False)
    df["geo_display_name"] = [g["display_name"] if u else None for g, u in zip(resolvidos, usa_geo)]
    achado = [g is not None and g["nivel"] != "falhou" for g in resolvidos]
    df["geo_nivel"] = [g["nivel"] if g is not None else None for g in resolvidos]
    df["geo_tentativa"] = [g["tentativa"] if g is not None and g["nivel"] != "falhou" else None for g in resolvidos]
    df["geo_bairro_confere"] = pd.Series([g["bairro_ok"] if a else None for g, a in zip(resolvidos, achado)],
                                         index=df.index, dtype="boolean")
    df["geo_rua_confere"] = pd.Series([g["rua_ok"] if a else None for g, a in zip(resolvidos, achado)],
                                      index=df.index, dtype="boolean")
    situacao = pd.Series(situacao, index=df.index)
    return {
        "consultas_no_cache": len(cache),
        "situacao_por_linha": situacao.value_counts().to_dict(),
        "geocode_descartado_rua_diferente": int((pd.Series(achado, index=df.index)
                                                 & ~df["geo_rua_confere"].fillna(True)).sum()),
        "top20_enderecos_que_falharam": (df.loc[situacao == "falhou", "endereco_norm"]
                                         .value_counts().head(20).to_dict()),
    }


def ano_fora_do_arquivo(raw: pd.DataFrame) -> dict[str, int]:
    """Rows whose date year differs from the file they came from (e.g. 2025-12 in the 2024 CSV)."""
    ano = pd.to_datetime(raw["data"], format="%Y-%m-%d", errors="coerce").dt.year
    fora = raw[ano.notna() & (ano != raw["ano_arquivo"])]
    pares = zip(fora["ano_arquivo"], ano[fora.index].astype(int))
    return pd.Series([f"arquivo {a} -> data {d}" for a, d in pares]).value_counts().to_dict()


def build() -> tuple[pd.DataFrame, dict]:
    raw, stats = load_sinistros()
    semaforos, ajustes_semaforo = load_semaforos()

    counts, invalidos = {}, {}
    for col in COUNT_COLS:
        counts[col], invalidos[col] = parse_numbers(raw[col])

    criterio = criterio_atropelamento(raw["tipo"].fillna(""), counts["pedestre"])
    mask = criterio.notna()
    animal = raw["tipo"].fillna("").map(ascii_upper).str.contains("ATROPELAMENTO.*ANIMAL")
    df = raw[mask].copy()
    for col in COUNT_COLS:
        df[col] = counts[col][mask].round().astype("Int64")
    df["criterio_atropelamento"] = criterio[mask]

    df["protocolo"] = df["protocolo"].map(normalize_num_semaforo)
    dt = pd.to_datetime(df["data"], format="%Y-%m-%d", errors="coerce")
    hm = df["hora"].fillna("").str.extract(r"^(\d{1,2}):(\d{2})")
    hora = pd.to_numeric(hm[0], errors="coerce")
    minuto = pd.to_numeric(hm[1], errors="coerce")
    hora_ok = hora.between(0, 23) & minuto.between(0, 59)
    df["hora"] = hora.where(hora_ok).astype("Int64")
    df["datahora"] = (dt + pd.to_timedelta(hora.where(hora_ok), unit="h")
                      + pd.to_timedelta(minuto.where(hora_ok), unit="m"))
    df["data"] = dt.dt.date
    df["ano"] = dt.dt.year.astype("Int64")
    df["mes"] = dt.dt.month.astype("Int64")
    df["dia_semana"] = dt.dt.day_of_week.astype("Int64")
    inicio = (df["hora"] // 3) * 3
    df["faixa_horaria"] = [None if pd.isna(h) else f"{h:02d}-{h + 3:02d}" for h in inicio]

    df["gravidade"] = gravidade(df["natureza"], df["vitimas"], df["vitimasfatais"])
    df["endereco_norm"] = df["endereco"].map(normalize_endereco)
    df["num_semaforo_norm"] = df["num_semaforo"].map(normalize_num_semaforo)

    df = df.merge(semaforos, how="left", left_on="num_semaforo_norm", right_on="semaforo_norm")
    df["lat_semaforo"], df["lon_semaforo"] = df.pop("latitude"), df.pop("longitude")
    tem_coord = df["lat_semaforo"].notna()
    confere = [
        (ascii_upper(b) == sb) or bool(street_tokens(e) & st)
        for b, e, sb, st in zip(df["bairro"], df["endereco"], df["sem_bairro"].fillna(""),
                                df["sem_tokens"].map(lambda t: t if isinstance(t, set) else set()))
    ]
    df["coord_confere"] = pd.Series(confere, index=df.index, dtype="boolean").where(tem_coord)
    casou = df["semaforo_norm"].notna()
    df["local_id"] = [
        f"sem-{s}" if c else f"end-{slug(e)}-{slug(b)}"
        for c, s, e, b in zip(casou, df["num_semaforo_norm"], df["endereco_norm"], df["bairro"])
    ]

    # 2022+ exports house numbers as '229,0'; drop that float artifact, keep anything else as-is.
    df["numero"] = df["numero"].str.replace(r"^(\d+)[.,]0+$", r"\1", regex=True)
    for col in ("natureza", "tipo", "bairro", "endereco", "numero", "bairro_cruzamento"):
        df[col] = df[col].replace("", None)

    geo_stats = add_coordenada_final(df)

    stats.update({
        "geocodificacao": geo_stats,
        "valores_numericos_invalidos_toda_base": invalidos,
        "ajustes_semaforo": ajustes_semaforo,
        "tipo_das_linhas_incluidas": raw.loc[mask, "tipo"].value_counts().to_dict(),
        "atropelamento_animal_excluido": int((animal & ~mask).sum()),
        "atropelamento_animal_mantido_por_pedestre": int((animal & mask).sum()),
        "linhas_com_ano_diferente_do_arquivo_toda_base": ano_fora_do_arquivo(raw),
        "data_invalida": int(dt.isna().sum()),
        "num_semaforo_sem_par": df.loc[df["num_semaforo_norm"].notna() & ~casou, "num_semaforo"].tolist(),
        "protocolo_duplicado": int(df["protocolo"].dropna().duplicated().sum()),
    })
    return df[OUTPUT_COLS].reset_index(drop=True), stats


def quality_report(df: pd.DataFrame, stats: dict) -> dict:
    por_ano = df.groupby("ano")
    pct = lambda s: round(float(s.mean()) * 100, 1)  # noqa: E731
    return {
        "gerado_em": pd.Timestamp.now(tz="America/Recife").isoformat(),
        "total": int(len(df)),
        "atropelamentos_por_ano": {str(k): int(v) for k, v in por_ano.size().items()},
        "pct_com_coordenada_por_ano": {str(k): pct(g["lat"].notna()) for k, g in por_ano},
        "pct_com_coordenada_total": pct(df["lat"].notna()),
        "pct_com_coordenada_antes_geocode_por_ano": {str(k): pct(g["lat_semaforo"].notna()) for k, g in por_ano},
        "pct_com_coordenada_antes_geocode_total": pct(df["lat_semaforo"].notna()),
        "pct_precisao_alta_ou_media_por_ano": {str(k): pct(g["coord_precisao"].isin(["alta", "media"]))
                                               for k, g in por_ano},
        "por_coord_fonte": {("sem_coordenada" if pd.isna(k) else k): int(v)
                            for k, v in df["coord_fonte"].value_counts(dropna=False).items()},
        "por_coord_precisao": {("sem_coordenada" if pd.isna(k) else k): int(v)
                               for k, v in df["coord_precisao"].value_counts(dropna=False).items()},
        "pct_hora_valida_total": pct(df["hora"].notna()),
        "pct_hora_valida_por_ano": {str(k): pct(g["hora"].notna()) for k, g in por_ano},
        "top15_local_id": {k: int(v) for k, v in df["local_id"].value_counts().head(15).items()},
        "por_criterio_atropelamento": {k: int(v) for k, v in df["criterio_atropelamento"].value_counts().items()},
        "por_gravidade": {k: int(v) for k, v in df["gravidade"].value_counts().items()},
        "coord_confere": {("sem_coordenada" if pd.isna(k) else str(k)): int(v)
                          for k, v in df["coord_confere"].value_counts(dropna=False).items()},
        "local_ids_distintos": int(df["local_id"].nunique()),
        "diagnostico_fonte": stats,
        "ressalvas": RESSALVAS,
    }


def write_parquet(df: pd.DataFrame) -> None:
    table = pa.Table.from_pandas(df, preserve_index=False)
    meta = dict(table.schema.metadata or {})
    meta[b"ressalvas"] = json.dumps(RESSALVAS, ensure_ascii=False).encode()
    meta[b"documentacao"] = b"docs/11-base-atropelamentos.md"
    pq.write_table(table.replace_schema_metadata(meta), OUT_PARQUET)


def write_amostra(df: pd.DataFrame, n: int = 30) -> None:
    """Random sample of rows with a coordinate + OSM link, for the group to check by hand."""
    com = df[df["lat"].notna()]
    amostra = com.sample(min(n, len(com)), random_state=SEED)[
        ["protocolo", "data", "bairro", "endereco", "numero", "num_semaforo_norm", "coord_fonte",
         "coord_precisao", "geo_display_name", "lat", "lon"]].copy()
    amostra["link_osm"] = [f"https://www.openstreetmap.org/?mlat={la}&mlon={lo}#map=18/{la}/{lo}"
                           for la, lo in zip(amostra["lat"], amostra["lon"])]
    amostra["conferido_ok"] = ""
    amostra["observacao"] = ""
    amostra.to_csv(OUT_AMOSTRA, index=False, encoding="utf-8")


def print_report(rep: dict) -> None:
    print(f"atropelamentos: {rep['total']}  |  com coordenada: {rep['pct_com_coordenada_total']}%  |  "
          f"hora valida: {rep['pct_hora_valida_total']}%")
    print("\nano   total  %coord_antes  %coord_depois  %alta_media  %hora")
    for ano, n in rep["atropelamentos_por_ano"].items():
        print(f"{ano}  {n:6d}  {rep['pct_com_coordenada_antes_geocode_por_ano'][ano]:11.1f}"
              f"  {rep['pct_com_coordenada_por_ano'][ano]:13.1f}  {rep['pct_precisao_alta_ou_media_por_ano'][ano]:10.1f}"
              f"  {rep['pct_hora_valida_por_ano'][ano]:5.1f}")
    print("\ncoord_fonte:", rep["por_coord_fonte"])
    print("coord_precisao:", rep["por_coord_precisao"])
    geo = rep["diagnostico_fonte"]["geocodificacao"]
    print("geocode por linha:", geo["situacao_por_linha"], "| descartado (rua diferente):",
          geo["geocode_descartado_rua_diferente"])
    print("\ncriterio:", rep["por_criterio_atropelamento"])
    print("gravidade:", rep["por_gravidade"])
    print("coord_confere:", rep["coord_confere"])
    print("\ntop 15 local_id:")
    for k, v in rep["top15_local_id"].items():
        print(f"  {v:4d}  {k}")
    print("\nressalvas:")
    for r in rep["ressalvas"]:
        print(f"  - {r}")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data, diag = build()
    write_parquet(data)
    report = quality_report(data, diag)
    OUT_QUALIDADE.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print_report(report)
    write_amostra(data)
    print(f"\nwrote {OUT_PARQUET} ({len(data)} linhas), {OUT_QUALIDADE} e {OUT_AMOSTRA}")
