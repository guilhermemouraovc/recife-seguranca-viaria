import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_atropelamentos import (  # noqa: E402
    criterio_atropelamento,
    gravidade,
    normalize_endereco,
    normalize_num_semaforo,
)


@pytest.mark.parametrize("raw, expected", [
    ("Av. Eng. José Estelita,", "AV ENG JOSE ESTELITA"),
    ("AVENIDA  CAXANGÁ", "AV CAXANGA"),
    ("Rua da Aurora", "R DA AURORA"),
    ("R. DA AURORA", "R DA AURORA"),
    ("Estrada do Arraial", "EST DO ARRAIAL"),
    ("EST DO ARRAIAL", "EST DO ARRAIAL"),
    ("Praça do Derby", "PCA DO DERBY"),
    ("pca. do derby", "PCA DO DERBY"),
    ("Av.Cruz Cabugá", "AV CRUZ CABUGA"),
    ("RUA 15 DE MARÇO", "R 15 DE MARCO"),
    ("", None),
    (None, None),
])
def test_normalize_endereco(raw, expected):
    assert normalize_endereco(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("37", "37"),
    ("037", "37"),
    ("009", "9"),
    ("37,0", "37"),
    ("510.0", "510"),
    (" 174 ", "174"),
    ("0", None),
    ("0,0", None),
    ("", None),
    ("S/N", None),
    ("37,5", None),
    (None, None),
])
def test_normalize_num_semaforo(raw, expected):
    assert normalize_num_semaforo(raw) == expected


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


def test_gravidade():
    natureza = pd.Series(["VÍTIMA FATAL", "COM VÍTIMA", "SEM VÍTIMA", "", "", "COM VÍTIMA", "VÍTIMA FATAL"])
    vitimas = pd.Series([0, 1, 0, 2, None, 1, None], dtype="Int64")
    fatais = pd.Series([None, 0, 0, None, None, 1, None], dtype="Int64")
    assert gravidade(natureza, vitimas, fatais).tolist() == [
        "fatal", "com_vitima", "sem_vitima", "com_vitima", "desconhecida", "fatal", "fatal",
    ]
