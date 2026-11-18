"""Métricas e gráficos da seção 5 do ARCHITECTURE.md.

Acurácia não é usada: com 2% a 25% de positivos, um modelo que diz "nenhum local tem
acidente" já passa de 75% de acurácia sem ranquear nada. A métrica principal é o PR-AUC
(average precision), comparado com a prevalência, que é o PR-AUC de um ranking aleatório.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sem display dentro do container
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import (ConfusionMatrixDisplay, PrecisionRecallDisplay, RocCurveDisplay,
                             average_precision_score, classification_report, confusion_matrix,
                             f1_score, precision_recall_curve, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import learning_curve

KS = (50, 100)


def no_topo(y: pd.Series, score: np.ndarray, trimestre: pd.Series, k: int) -> tuple[float, float]:
    """(recall@k, precisão@k), por trimestre e com média entre os trimestres.

    Em cada trimestre, os k locais de maior score: recall@k = acertos ÷ positivos do trimestre
    ("dos acidentes que houve, quantos estavam no top-k"); precisão@k = acertos ÷ k ("dos k
    locais apontados, quantos tiveram acidente"). Trimestre sem positivo não entra no recall.
    """
    df = pd.DataFrame({"y": np.asarray(y), "score": score, "tri": np.asarray(trimestre)})
    recalls, precisoes = [], []
    for _, g in df.groupby("tri"):
        acertos = g.nlargest(k, "score")["y"].sum()
        precisoes.append(acertos / min(k, len(g)))
        if g["y"].sum():
            recalls.append(acertos / g["y"].sum())
    return float(np.mean(recalls)), float(np.mean(precisoes))


def escolher_limiar(y: pd.Series, score: np.ndarray) -> float:
    """Limiar que maximiza o F1 na validação: equilibra encontrar os locais de risco e não
    encher a lista de alarmes falsos. É escolhido na validação e só aplicado no teste."""
    precisao, recall, limiares = precision_recall_curve(y, score)
    f1 = 2 * precisao * recall / np.clip(precisao + recall, 1e-12, None)
    return float(limiares[np.argmax(f1[:-1])])


def avaliar(y: pd.Series, score: np.ndarray, trimestre: pd.Series, limiar: float) -> dict:
    pred = (score >= limiar).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    m = {
        "pr_auc": average_precision_score(y, score),
        "roc_auc": roc_auc_score(y, score),
        "prevalencia": float(np.mean(y)),
        "limiar": limiar,
        "f1": f1_score(y, pred, zero_division=0),
        "precisao": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
    }
    for k in KS:
        m[f"recall_at_{k}"], m[f"precisao_at_{k}"] = no_topo(y, score, trimestre, k)
    return {k: float(v) for k, v in m.items()}


def relatorio(y: pd.Series, score: np.ndarray, limiar: float) -> str:
    return classification_report(y, (score >= limiar).astype(int), digits=3, zero_division=0)


def _salvar(fig, caminho: Path) -> Path:
    fig.tight_layout()
    fig.savefig(caminho, dpi=110)
    plt.close(fig)
    return caminho


def graficos(y: pd.Series, score: np.ndarray, limiar: float, pasta: Path, titulo: str) -> list[Path]:
    """Matriz de confusão, curva precisão-recall e curva ROC, em PNG."""
    pasta.mkdir(parents=True, exist_ok=True)
    saidas = []
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay.from_predictions(y, (score >= limiar).astype(int), ax=ax, colorbar=False)
    ax.set_title(f"{titulo}\nlimiar {limiar:.3f}", fontsize=9)
    saidas.append(_salvar(fig, pasta / "matriz_confusao.png"))
    fig, ax = plt.subplots(figsize=(5, 4))
    PrecisionRecallDisplay.from_predictions(y, score, ax=ax, plot_chance_level=True)
    ax.set_title(titulo, fontsize=9)
    saidas.append(_salvar(fig, pasta / "curva_precisao_recall.png"))
    fig, ax = plt.subplots(figsize=(5, 4))
    RocCurveDisplay.from_predictions(y, score, ax=ax, plot_chance_level=True)
    ax.set_title(titulo, fontsize=9)
    saidas.append(_salvar(fig, pasta / "curva_roc.png"))
    return saidas


def curva_aprendizado(pipe, X: pd.DataFrame, y: pd.Series, folds: list, caminho: Path, titulo: str) -> Path:
    """PR-AUC de treino × validação com fatias crescentes do treino de cada fold temporal."""
    tamanhos, treino, validacao = learning_curve(pipe, X, y, cv=folds, train_sizes=[0.33, 0.66, 1.0],
                                                 scoring="average_precision", n_jobs=1)
    fig, ax = plt.subplots(figsize=(5, 4))
    for nome, s in [("treino", treino), ("validação (folds temporais)", validacao)]:
        ax.plot(tamanhos, s.mean(axis=1), marker="o", label=nome)
        ax.fill_between(tamanhos, s.mean(axis=1) - s.std(axis=1), s.mean(axis=1) + s.std(axis=1), alpha=.2)
    ax.set(xlabel="linhas de treino", ylabel="PR-AUC", title=titulo)
    ax.legend()
    return _salvar(fig, caminho)


def barras_comparacao(tabela: pd.DataFrame, caminho: Path, titulo: str) -> Path:
    """Uma barra por modelo e métrica (PR-AUC, recall@50, recall@100, ROC-AUC)."""
    cols = ["pr_auc", "recall_at_50", "recall_at_100", "roc_auc"]
    fig, ax = plt.subplots(figsize=(8, 4))
    tabela[cols].astype(float).plot.bar(ax=ax)
    if "prevalencia" in tabela:
        ax.axhline(float(tabela["prevalencia"].iloc[0]), color="gray", ls="--", lw=1,
                   label="prevalência (PR-AUC aleatório)")
    ax.set(title=titulo, ylabel="valor na validação", ylim=(0, 1))
    ax.legend(fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    return _salvar(fig, caminho)


def importancia_permutacao(pipe, X: pd.DataFrame, y: pd.Series, caminho: Path, titulo: str,
                           top: int = 20) -> tuple[Path, pd.Series]:
    """Queda de PR-AUC ao embaralhar cada coluna original (antes do one-hot)."""
    r = permutation_importance(pipe, X, y, scoring="average_precision", n_repeats=5, random_state=42, n_jobs=1)
    imp = pd.Series(r.importances_mean, index=X.columns).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(6, 6))
    imp.head(top).iloc[::-1].plot.barh(ax=ax)
    ax.set(title=titulo, xlabel="queda média de PR-AUC")
    return _salvar(fig, caminho), imp
