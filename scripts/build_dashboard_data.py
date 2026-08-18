"""Aggregates downloaded raw CSVs into web/data.json for the visualization dashboard.

Only summarizes what has actually been fetched into data/raw/ -- re-run after
each new dataset lands to extend the dashboard. Preserves the methodological
caveats from docs/06-limitacoes-metodologicas.md as fields in the JSON so the
frontend can render them next to the numbers, not hide them.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SINISTROS_DIR = ROOT / "data" / "raw" / "cttu" / "acidentes-de-transito-com-e-sem-vitimas"
OUT_PATH = ROOT / "web" / "data.json"


def build_sinistros_summary() -> dict:
    """Per-year totals from the consolidated sinistros dataset (2015-2024).

    Column names drift across years (docs/06 #9: form changes over time) --
    e.g. 'DATA' vs 'data', 'natureza' vs 'natureza_acidente', and 2015 has no
    'vitimasfatais' column at all. Normalize names; treat a missing column as
    unknown (None), never as zero.
    """
    by_year = []
    for csv_path in sorted(SINISTROS_DIR.glob("*.csv")):
        df = pd.read_csv(csv_path, sep=";", decimal=",")
        df.columns = df.columns.str.lower()
        df = df.rename(columns={"natureza_acidente": "natureza"})
        year = int(df["data"].str.slice(0, 4).mode()[0])
        if year == 2015:
            # Source anomaly, confirmed by inspection: in this file 'tipo' holds
            # COM/SEM VITIMA/VITIMA FATAL and 'natureza' holds the accident type
            # (COLISAO, ATROPELAMENTO...) -- the reverse of every other year.
            df = df.rename(columns={"natureza": "_tipo_2015", "tipo": "natureza"})
        has_fatais = "vitimasfatais" in df.columns
        by_year.append({
            "ano": year,
            "sinistros": int(len(df)),
            "vitimas": float(df["vitimas"].sum()),
            "vitimas_fatais": float(df["vitimasfatais"].sum()) if has_fatais else None,
            "natureza": df["natureza"].value_counts().to_dict(),
        })
    by_year.sort(key=lambda row: row["ano"])
    return by_year


if __name__ == "__main__":
    data = {
        "generated_at": pd.Timestamp.now("UTC").isoformat(),
        "sinistros_por_ano": build_sinistros_summary(),
        "caveats": [
            "2015 so tem dados a partir de junho -- qualquer total anual de 2015 esta subestimado.",
            "Sao dados de 'chamados' da CTTU, podem divergir dos Relatorios Anuais oficiais (registros dos agentes de transito).",
            "2025, quando presente, e classificado como preliminar pelo PSVR.",
            "O CSV de 2015 nao tem coluna 'vitimasfatais' -- valor tratado como desconhecido (null), nao zero.",
            "No CSV de 2015 as colunas 'tipo' e 'natureza' vem trocadas em relacao aos demais anos (confirmado por inspecao) -- corrigido no pipeline antes de agregar.",
            "Nomes de coluna mudam entre anos (data/DATA, natureza/natureza_acidente) -- normalizado no pipeline, nao na fonte.",
            "Fonte: Portal de Dados Abertos do Recife (CKAN), dataset acidentes-de-transito-com-e-sem-vitimas.",
        ],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT_PATH} ({len(data['sinistros_por_ano'])} years)")
