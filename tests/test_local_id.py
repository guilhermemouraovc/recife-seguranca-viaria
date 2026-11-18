"""Tests for src/preparo/local_id.py (no files, no network)."""
import hashlib

import pandas as pd

from src.preparo.local_id import gerar_local_id, normalizar_logradouro, normalizar_texto, preparar_acidentes


def test_local_id_igual_entre_grafias():
    logradouro = normalizar_logradouro(pd.Series(
        ["R. José  de Alencar", "RUA JOSE DE ALENCAR", "Av. Caxangá", "AVENIDA CAXANGA", "TV. do Ouvidor", "RUA", None]))
    assert logradouro.iloc[:5].tolist() == ["JOSE DE ALENCAR"] * 2 + ["CAXANGA"] * 2 + ["DO OUVIDOR"]
    assert logradouro.iloc[5:].isna().all()

    ids = gerar_local_id(normalizar_texto(pd.Series(["Boa Viagem", "BOA  VIAGEM", None])),
                         normalizar_logradouro(pd.Series(["Av. Conselheiro Aguiar", "AVENIDA CONSELHEIRO AGUIAR", "R X"])))
    assert ids.iloc[0] == ids.iloc[1] == hashlib.sha1(b"BOA VIAGEM|CONSELHEIRO AGUIAR").hexdigest()[:12]
    assert pd.isna(ids.iloc[2])


def test_preparar_acidentes_exclui_o_que_nao_conta():
    sinistros = pd.DataFrame({
        "situacao": ["FINALIZADA", "CANCELADA", "DUPLICIDADE", "FINALIZADA", "FINALIZADA"],
        "data_fora_do_ano_arquivo": [False, False, False, True, False],
        "bairro": ["PINA", "PINA", "PINA", "PINA", None],
        "endereco": ["AV X", "AV X", "AV X", "AV X", "AV X"],
        "data": pd.to_datetime(["2020-01-05", "2020-01-05", "2020-01-05", "2025-12-01", "2020-04-01"]),
        "vitimas": pd.array([1, 0, 0, 0, 0], dtype="Int64"),
        "vitimasfatais": pd.array([None, 0, 0, 0, 1], dtype="Int64"),
    })
    acidentes, exclusoes = preparar_acidentes(sinistros)
    assert exclusoes == {"situacao_excluida": {"CANCELADA": 1, "DUPLICIDADE": 1},
                         "data_fora_do_ano_arquivo": 1, "sem_bairro_ou_logradouro": 1}
    assert acidentes["trimestre"].tolist() == ["2020Q1", "2020Q2"]
    assert acidentes["com_vitima"].tolist() == [True, True]
    assert acidentes["fatal"].tolist() == [False, True]
    assert acidentes["local_id"].isna().tolist() == [False, True]
