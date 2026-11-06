"""Tests for scripts/clean_sinistros.py (no files, no network)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from clean_sinistros import clean, criterio_atropelamento  # noqa: E402


def test_criterio_atropelamento():
    df = pd.DataFrame([
        ("ATROPELAMENTO", 1),
        ("ATROPELAMENTO DE PESSOA", None),
        ("COLISÃO", 2),
        ("ATROPELAMENTO ANIMAL", 0),
        ("ATROPELAMENTO DE ANIMAL", 1),
        ("COLISÃO", 0),
        ("", None),
        ("atropelamento", 0),
    ], columns=["tipo", "pedestre"])
    assert criterio_atropelamento(df["tipo"], df["pedestre"]).tolist() == [
        "tipo+pedestre", "tipo", "pedestre", None, "pedestre", None, None, "tipo",
    ]


def _raw(rows):
    cols = ["data", "hora", "gravidade", "tipo_acidente", "bairro", "endereco", "numero", "pedestre"]
    raw = pd.DataFrame(rows, columns=cols).astype(str)
    raw["ano_arquivo"] = 2019
    return raw


def test_clean_nao_muda_flag_atropelamento():
    out = clean(_raw([
        ("2019-01-01", "10:00:00", "COM VÍTIMA", "ATROPELAMENTO", "PINA", "AV X", "", "1"),
        ("2019-01-01", "10:00:00", "COM VÍTIMA", "COLISÃO", "PINA", "AV X", "", "1"),
        ("2019-01-01", "10:00:00", "COM VÍTIMA", "ATROPELAMENTO ANIMAL", "PINA", "AV X", "", ""),
    ]))
    assert out["atropelamento"].tolist() == [True, False, False]
    assert out["criterio_atropelamento"].tolist() == ["tipo+pedestre", "pedestre", None]
