"""Pré-processamento e modelos (ARCHITECTURE.md, seções 3.4 e 6).

Tudo num Pipeline + ColumnTransformer ajustado só no treino (tests/test_modelagem.py garante):
numéricas com mediana do treino e StandardScaler; categóricas com DESCONHECIDO e one-hot;
bairro com one-hot nos 20 mais frequentes e OUTROS no resto.
"""
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src.preparo.features import ALVOS, MODAS, VIA_CATEGORICAS

SEMENTE = 42
IDENTIFICADORES = ["local_id", "trimestre"]
CATEGORICAS = VIA_CATEGORICAS + list(MODAS.values())
BAIRRO = "bairro"
# max_categories junta as categorias raras numa coluna "infrequente": no bairro, 20 + OUTROS;
# nas demais só pesa em sentido_via (92 valores) e situacao_placa (29).
MAX_CATEGORIAS, MAX_BAIRROS = 15, 21


def colunas_do_modelo(features: pd.DataFrame) -> tuple[list[str], list[str]]:
    """(numéricas, categóricas) que entram no modelo. Telemetria (tel_*) fica de fora nesta
    fase: não cobre nenhum trimestre de treino (ARCHITECTURE.md, seção 17.4)."""
    fora = set(IDENTIFICADORES) | set(ALVOS) | set(CATEGORICAS) | {BAIRRO}
    numericas = [c for c in features if c not in fora and not c.startswith("tel_")]
    return numericas, [c for c in CATEGORICAS if c in features]


def matriz(features: pd.DataFrame) -> pd.DataFrame:
    """Recorte das colunas do modelo com tipos que o scikit-learn aceita (bool e Int64 viram float)."""
    numericas, categoricas = colunas_do_modelo(features)
    return pd.concat([features[numericas].astype("float64"),
                      features[categoricas + [BAIRRO]].astype("object")], axis=1)


def preprocessador(features: pd.DataFrame) -> ColumnTransformer:
    numericas, categoricas = colunas_do_modelo(features)
    def categorico(maximo: int) -> Pipeline:
        return make_pipeline(
            SimpleImputer(strategy="constant", fill_value="DESCONHECIDO"),
            OneHotEncoder(handle_unknown="infrequent_if_exist", max_categories=maximo, sparse_output=False))
    return ColumnTransformer([
        ("numericas", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), numericas),
        ("categoricas", categorico(MAX_CATEGORIAS), categoricas),
        ("bairro", categorico(MAX_BAIRROS), [BAIRRO]),
    ])


def modelos() -> dict:
    """Baseline e os cinco da comparação. class_weight='balanced' onde o modelo aceita; o
    AdaBoost recebe o balanceamento pela árvore base. KNN e MLP não têm o parâmetro."""
    return {
        "regressao_logistica": LogisticRegression(class_weight="balanced", max_iter=1000),
        "knn": KNeighborsClassifier(n_neighbors=50, weights="distance"),
        "arvore_decisao": DecisionTreeClassifier(class_weight="balanced", max_depth=6, min_samples_leaf=50,
                                                 random_state=SEMENTE),
        "random_forest": RandomForestClassifier(n_estimators=300, class_weight="balanced_subsample",
                                                min_samples_leaf=10, n_jobs=-1, random_state=SEMENTE),
        "adaboost": AdaBoostClassifier(estimator=DecisionTreeClassifier(max_depth=2, class_weight="balanced"),
                                       n_estimators=200, learning_rate=0.5, random_state=SEMENTE),
        "mlp": MLPClassifier(hidden_layer_sizes=(64, 32), alpha=1e-3, early_stopping=True, max_iter=500,
                             random_state=SEMENTE),
    }


def montar_pipeline(features: pd.DataFrame, nome: str, **params) -> Pipeline:
    modelo = modelos()[nome]
    return Pipeline([("prep", preprocessador(features)), ("modelo", modelo.set_params(**params))])
