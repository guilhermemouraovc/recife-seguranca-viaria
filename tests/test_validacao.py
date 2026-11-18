"""Tests for src/modelagem/validacao.py: temporal folds never train on the future."""
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from src.modelagem.validacao import folds_temporais, split_temporal


def _painel(n_locais: int = 30, trimestres: tuple = ("2021Q1", "2021Q2", "2021Q3", "2021Q4",
                                                       "2022Q1", "2022Q2", "2022Q3", "2022Q4")) -> pd.Series:
    # Ordem embaralhada de propósito: os folds não podem depender da ordem das linhas.
    tri = pd.Series(np.repeat(trimestres, n_locais))
    return tri.sample(frac=1, random_state=0).reset_index(drop=True)


def test_folds_temporais_treino_sempre_antes_da_validacao():
    tri = _painel()
    folds = list(folds_temporais(tri, minimo_treino=4))
    assert len(folds) == 4  # valida em 2022Q1, 2022Q2, 2022Q3 e 2022Q4
    for i, (treino, validacao) in enumerate(folds):
        assert tri.iloc[treino].max() < tri.iloc[validacao].min()
        assert tri.iloc[validacao].nunique() == 1  # valida num trimestre inteiro, não em parte dele
        assert tri.iloc[treino].nunique() == 4 + i  # janela crescente
        assert not set(treino) & set(validacao)


def test_kfold_estratificado_vaza_o_futuro_no_painel():
    """O contraste da seção 4: no painel, o k-fold estratificado treina com trimestres futuros."""
    tri = _painel()
    y = (np.arange(len(tri)) % 5 == 0).astype(int)
    vazou = [tri.iloc[treino].max() > tri.iloc[validacao].min()
             for treino, validacao in StratifiedKFold(5, shuffle=True, random_state=0).split(tri, y)]
    assert all(vazou)


def test_split_temporal_por_trimestre_e_sem_alvo_nulo():
    tri = ["2020Q4", "2021Q1", "2022Q4", "2023Q2", "2024Q3", "2024Q4"]
    f = pd.DataFrame({"local_id": "a", "trimestre": tri, "y_vitima": [1, 0, 1, 0, 1, None]})
    partes = split_temporal(f, "y_vitima")
    assert {k: v["trimestre"].tolist() for k, v in partes.items()} == {
        "treino": ["2021Q1", "2022Q4"], "validacao": ["2023Q2"], "teste": ["2024Q3"]}
