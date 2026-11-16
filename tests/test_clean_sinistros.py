"""Tests for src/preparo/clean_sinistros.py (no files, no network)."""
import pandas as pd

from src.preparo.clean_sinistros import clean, criterio_atropelamento, normalizar_schema


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


def test_normalizar_schema():
    raw, colunas_por_ano = normalizar_schema({
        2018: pd.DataFrame({"DATA": ["2018-01-01"], "Endereço Cruzamento ": ["RUA A"], "tipo": ["COLISÃO"],
                            "natureza_acidente": ["COM VÍTIMA"]}),
        2015: pd.DataFrame({"data": ["2015-06-01"], "tipo": ["SEM VÍTIMA"], "natureza": ["COLISÃO"]}),
    })
    assert colunas_por_ano == {2015: ["data", "tipo", "natureza"],
                               2018: ["DATA", "Endereço Cruzamento ", "tipo", "natureza_acidente"]}
    assert raw["data"].tolist() == ["2015-06-01", "2018-01-01"]
    assert raw["endereco_cruzamento"].isna().tolist() == [True, False]
    assert raw["gravidade"].tolist() == ["SEM VÍTIMA", "COM VÍTIMA"]
    assert raw["tipo_acidente"].tolist() == ["COLISÃO", "COLISÃO"]


def test_acidente_verificado_nao_filtra():
    raw = _raw([
        ("2017-01-01", "10:00:00", "COM VÍTIMA", "COLISÃO", "PINA", "AV X", "", "0"),
        ("2018-01-01", "10:00:00", "COM VÍTIMA", "COLISÃO", "PINA", "AV X", "", "0"),
    ])
    raw["acidente_verificado"] = [float("nan"), "Longo da via"]
    out = clean(raw)
    assert out["acidente_verificado"].tolist() == ["DESCONHECIDO", "Longo da via"]
