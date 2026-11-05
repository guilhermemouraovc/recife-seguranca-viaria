"""Shared reader for the consolidated sinistros CSVs (acidentes-de-transito-com-e-sem-vitimas).

Column names drift across years (docs/06 #9: form changes over time) -- e.g.
'DATA' vs 'data', 'natureza' vs 'natureza_acidente', and 2015 has no
'vitimasfatais' column at all. Every script that reads these files goes
through normalize_columns() so the fixes live in one place.
"""
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SINISTROS_DIR = ROOT / "data" / "raw" / "cttu" / "acidentes-de-transito-com-e-sem-vitimas"


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Lowercase/rename columns, undo the 2015 tipo/natureza swap; returns (df, file year)."""
    df.columns = df.columns.str.lower()
    df = df.rename(columns={"natureza_acidente": "natureza"})
    year = int(df["data"].str.slice(0, 4).mode()[0])
    if year == 2015:
        # Source anomaly, confirmed by inspection: in this file 'tipo' holds
        # COM/SEM VITIMA/VITIMA FATAL and 'natureza' holds the accident type
        # (COLISAO, ATROPELAMENTO...) -- the reverse of every other year.
        df = df.rename(columns={"natureza": "tipo", "tipo": "natureza"})
    return df, year


def read_all(**read_csv_kwargs) -> Iterator[tuple[int, pd.DataFrame]]:
    """(file year, normalized DataFrame) for every yearly CSV, oldest first."""
    for csv_path in sorted(SINISTROS_DIR.glob("*.csv")):
        df, year = normalize_columns(pd.read_csv(csv_path, sep=";", **read_csv_kwargs))
        yield year, df
