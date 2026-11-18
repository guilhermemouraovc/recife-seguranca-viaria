"""Divisão temporal e validação cruzada temporal (ARCHITECTURE.md, seção 4).

O painel tem o mesmo local em vários trimestres, então k-fold estratificado põe trimestres
futuros no treino e passados na validação. TimeSeriesSplit também não serve: ele corta por
posição de linha, e cada trimestre tem 1.673 linhas. Aqui os folds andam sobre os trimestres
distintos, em janela crescente. tests/test_validacao.py garante que, em todo fold, o treino
termina antes de a validação começar.
"""
from collections.abc import Iterator

import numpy as np
import pandas as pd

# Corte em 2021Q1: primeiro trimestre com a janela de histórico de 4 trimestres inteira depois da
# quebra de série de 2020Q2 (ARCHITECTURE.md, seção 17.1).
PERIODOS = {
    "treino": ("2021Q1", "2022Q4"),
    "validacao": ("2023Q1", "2023Q4"),
    "teste": ("2024Q1", "2024Q4"),  # 2024Q4 não tem alvo (é a linha de scoring) e sai no dropna
}
MINIMO_TRIMESTRES_TREINO = 4


def split_temporal(features: pd.DataFrame, alvo: str) -> dict[str, pd.DataFrame]:
    """Treino, validação e teste por intervalo de trimestres, só com linhas de alvo conhecido."""
    rotulado = features.dropna(subset=[alvo]).sort_values(["trimestre", "local_id"], kind="stable")
    return {nome: rotulado[rotulado["trimestre"].between(ini, fim)].reset_index(drop=True)
            for nome, (ini, fim) in PERIODOS.items()}


def folds_temporais(trimestres: pd.Series,
                    minimo_treino: int = MINIMO_TRIMESTRES_TREINO) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Janela crescente sobre os trimestres distintos: o fold i treina nos trimestres
    [0 .. k+i] e valida no trimestre k+i+1, com k+1 = minimo_treino.

    Devolve posições (não rótulos do índice), como o cv= do scikit-learn espera. É um gerador:
    para reusar os folds (Optuna, várias chamadas), materialize com list().
    """
    valores = np.asarray(trimestres)
    unicos = np.sort(pd.unique(valores))
    for i in range(minimo_treino, len(unicos)):
        yield np.flatnonzero(np.isin(valores, unicos[:i])), np.flatnonzero(valores == unicos[i])
