"""Baseline, comparação, otimização e registro do campeão (ARCHITECTURE.md, seções 4 a 7).

Cada função é uma tarefa da dag_treino e roda para os dois alvos. O estado passa entre as
tarefas por data/processed/modelagem/<alvo>.json. Toda validação cruzada é temporal
(folds_temporais); o k-fold estratificado roda só como contraste e vai para o MLflow com o
prefixo cv_estratificado_, para mostrar o quanto o vazamento temporal infla as métricas.

Linha de comando (tudo, os dois alvos): python -m src.modelagem.treino
"""
import json
import os
import tempfile
from pathlib import Path

import mlflow
import optuna
import pandas as pd
from mlflow.tracking import MlflowClient
from scipy.stats import loguniform, randint
from sklearn.base import clone
from sklearn.metrics import average_precision_score
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, cross_validate

from src.modelagem import metricas
from src.modelagem.pipeline import SEMENTE, matriz, montar_pipeline
from src.modelagem.validacao import folds_temporais, split_temporal
from src.preparo.features import ALVOS

ROOT = Path(__file__).resolve().parents[2]
ESTADO = ROOT / "data" / "processed" / "modelagem"
EXPERIMENTOS = {"baseline": "01_baseline", "comparacao": "02_comparacao_modelos",
                "otimizacao": "03_otimizacao_hiperparametros"}
BASELINE = "regressao_logistica"
# Baseline ingênuo (ARCHITECTURE.md, seção 17.9): ranquear pela recorrência recente, a heurística
# que a CTTU descreveu. Acidentes com vítima nos últimos 4 trimestres; o total de acidentes no
# mesmo período desempata (Recall@k depende da ordem entre empatados).
HEURISTICA = "heuristica_recorrencia"
COMPARADOS = ["knn", "arvore_decisao", "random_forest", "adaboost", "mlp"]
# Orçamento de busca (ARCHITECTURE.md, seção 17.5): 10 trials do Optuna por modelo; o RandomizedSearchCV
# é só a referência, com 5 sorteios.
N_TRIALS, N_SORTEIOS = 10, 5
# y_vitima é o primário: o atropelamento não tem positivos suficientes (ARCHITECTURE.md, seção 17.2).
NOME_REGISTRO = {"y_vitima": "risco-viario", "y_atropelamento": "risco-viario-atropelamento"}
ALIAS = "champion"
# O padrão do MLflow 3.18 (skops) recusa tipos como numpy.dtype, que o OneHotEncoder guarda.
# cloudpickle serializa qualquer pipeline; os modelos só são lidos do nosso próprio registry.
FORMATO = mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE

ESPACOS = {
    "regressao_logistica": lambda t: {"C": t.suggest_float("C", 1e-3, 10, log=True)},
    "knn": lambda t: {"n_neighbors": t.suggest_int("n_neighbors", 10, 300, log=True),
                      "weights": t.suggest_categorical("weights", ["uniform", "distance"])},
    "arvore_decisao": lambda t: {"max_depth": t.suggest_int("max_depth", 2, 12),
                                 "min_samples_leaf": t.suggest_int("min_samples_leaf", 5, 300, log=True)},
    "random_forest": lambda t: {"n_estimators": t.suggest_int("n_estimators", 100, 300, step=50),
                                "max_depth": t.suggest_int("max_depth", 4, 16),
                                "min_samples_leaf": t.suggest_int("min_samples_leaf", 2, 60, log=True),
                                "max_features": t.suggest_categorical("max_features", ["sqrt", 0.3, 0.5])},
    "adaboost": lambda t: {"n_estimators": t.suggest_int("n_estimators", 50, 300, step=50),
                           "learning_rate": t.suggest_float("learning_rate", 0.05, 1.0, log=True),
                           "estimator__max_depth": t.suggest_int("estimator__max_depth", 1, 4)},
    "mlp": lambda t: {"hidden_layer_sizes": [int(n) for n in t.suggest_categorical(
                          "hidden_layer_sizes", ["32", "64", "64-32", "128-64"]).split("-")],
                      "alpha": t.suggest_float("alpha", 1e-5, 1e-1, log=True),
                      "learning_rate_init": t.suggest_float("learning_rate_init", 1e-4, 1e-2, log=True)},
}
SORTEIOS = {
    "regressao_logistica": {"C": loguniform(1e-3, 10)},
    "knn": {"n_neighbors": randint(10, 300), "weights": ["uniform", "distance"]},
    "arvore_decisao": {"max_depth": randint(2, 13), "min_samples_leaf": randint(5, 300)},
    "random_forest": {"n_estimators": randint(100, 301), "max_depth": randint(4, 17),
                      "min_samples_leaf": randint(2, 61), "max_features": ["sqrt", 0.3, 0.5]},
    "adaboost": {"n_estimators": randint(50, 301), "learning_rate": loguniform(0.05, 1.0),
                 "estimator__max_depth": randint(1, 5)},
    "mlp": {"hidden_layer_sizes": [(32,), (64,), (64, 32), (128, 64)], "alpha": loguniform(1e-5, 1e-1),
            "learning_rate_init": loguniform(1e-4, 1e-2)},
}


def _mlflow() -> None:
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000"))


def carregar_features() -> pd.DataFrame:
    from src.comum.db import engine

    return pd.read_sql_table("features", engine())


def _estado(alvo: str, *, zerar: bool = False, **novo) -> dict:
    """Lê o estado do alvo e, se vier `novo`, grava por cima as chaves dadas (com `zerar`, só elas)."""
    caminho = ESTADO / f"{alvo}.json"
    estado = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() and not zerar else {}
    if novo:
        ESTADO.mkdir(parents=True, exist_ok=True)
        estado.update(novo)
        # Arquivo temporário + os.replace: quem lê ao mesmo tempo vê o JSON antigo ou o novo, nunca pela metade.
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=ESTADO, suffix=".tmp", delete=False) as tmp:
            json.dump(estado, tmp, ensure_ascii=False, indent=2)
        os.replace(tmp.name, caminho)
    return estado


def _dados(alvo: str, features: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict, list]:
    features = carregar_features() if features is None else features
    partes = split_temporal(features, alvo)
    return features, partes, list(folds_temporais(partes["treino"]["trimestre"]))


def _xy(parte: pd.DataFrame, alvo: str) -> tuple[pd.DataFrame, pd.Series]:
    return matriz(parte), parte[alvo].astype(int)


def _cv(pipe, X, y, folds, prefixo: str = "cv_temporal") -> dict:
    r = cross_validate(clone(pipe), X, y, cv=folds, scoring={"pr_auc": "average_precision", "roc_auc": "roc_auc"})
    return {f"{prefixo}_{m}_{f}": float(getattr(r[f"test_{m}"], f)()) for m in ("pr_auc", "roc_auc")
            for f in ("mean", "std")}


def _cv_estratificado(pipe, X, y) -> dict:
    """O contraste da seção 4: o mesmo modelo com k-fold estratificado, que vaza o futuro."""
    return _cv(pipe, X, y, StratifiedKFold(5, shuffle=True, random_state=SEMENTE), "cv_estratificado")


def _rodar(nome_run: str, alvo: str, pipe, partes: dict, params: dict, extras: dict, tags: dict,
           folds: list | None = None) -> tuple[str, dict]:
    """Treina no treino, avalia na validação e registra um run completo no MLflow: parâmetros,
    métricas da seção 5, gráficos, classification_report e o modelo."""
    Xtr, ytr = _xy(partes["treino"], alvo)
    Xv, yv = _xy(partes["validacao"], alvo)
    pipe.fit(Xtr, ytr)
    score = pipe.predict_proba(Xv)[:, 1]
    limiar = metricas.escolher_limiar(yv, score)
    m = metricas.avaliar(yv, score, partes["validacao"]["trimestre"], limiar)
    titulo = f"{nome_run} | {alvo} | validação 2023"
    with mlflow.start_run(run_name=nome_run, tags={"alvo": alvo, **tags}) as run, \
            tempfile.TemporaryDirectory() as tmp:
        mlflow.log_params({k: str(v) for k, v in params.items()})
        mlflow.log_metrics({**{f"val_{k}": v for k, v in m.items()}, **extras})
        metricas.graficos(yv, score, limiar, Path(tmp), titulo)
        if folds:  # curva de aprendizado nos 2 maiores folds temporais (orçamento de tempo)
            metricas.curva_aprendizado(pipe, Xtr, ytr, folds[-2:], Path(tmp) / "curva_aprendizado.png", titulo)
        (Path(tmp) / "classification_report.txt").write_text(metricas.relatorio(yv, score, limiar), encoding="utf-8")
        mlflow.log_artifacts(tmp)
        mlflow.sklearn.log_model(pipe, name="modelo", input_example=Xtr.head(3), serialization_format=FORMATO)
    return run.info.run_id, m


def score_heuristica(parte: pd.DataFrame) -> pd.Series:
    """Score do baseline ingênuo: não aprende nada, só ordena pelo histórico recente do local."""
    return (parte["acidentes_vitima_4t"] + parte["acidentes_4t"] / 1000).astype("float64")


def _heuristica(alvo: str, partes: dict, folds: list) -> tuple[str, dict]:
    """Run do baseline ingênuo no experimento 01: mesmas métricas, folds e validação dos modelos."""
    treino, val = partes["treino"], partes["validacao"]
    ytr, yv = treino[alvo].astype(int), val[alvo].astype(int)
    score_tr, score_v = score_heuristica(treino), score_heuristica(val).to_numpy()
    aps = pd.Series([average_precision_score(ytr.iloc[v], score_tr.iloc[v]) for _, v in folds])
    extras = {"cv_temporal_pr_auc_mean": float(aps.mean()), "cv_temporal_pr_auc_std": float(aps.std(ddof=0))}
    limiar = metricas.escolher_limiar(yv, score_v)
    m = metricas.avaliar(yv, score_v, val["trimestre"], limiar)
    with mlflow.start_run(run_name=HEURISTICA, tags={"alvo": alvo, "etapa": "baseline"}) as run, \
            tempfile.TemporaryDirectory() as tmp:
        mlflow.log_params({"score": "acidentes_vitima_4t + acidentes_4t / 1000"})
        mlflow.log_metrics({**{f"val_{k}": v for k, v in m.items()}, **extras})
        metricas.graficos(yv, score_v, limiar, Path(tmp), f"{HEURISTICA} | {alvo} | validação 2023")
        (Path(tmp) / "classification_report.txt").write_text(metricas.relatorio(yv, score_v, limiar), encoding="utf-8")
        mlflow.log_artifacts(tmp)
    return run.info.run_id, {**m, **extras}


def _parametros(pipe) -> dict:
    return pipe.named_steps["modelo"].get_params(deep=False)


def treinar_baseline(features: pd.DataFrame | None = None) -> None:
    """Experimento 01: a Regressão Logística e o baseline ingênuo de recorrência, os pisos de
    comparação. O ingênuo fica fora do ranking da comparação (não tem o que otimizar)."""
    _mlflow()
    mlflow.set_experiment(EXPERIMENTOS["baseline"])
    for alvo in ALVOS:
        feats, partes, folds = _dados(alvo, features)
        Xtr, ytr = _xy(partes["treino"], alvo)
        pipe = montar_pipeline(feats, BASELINE)
        extras = {**_cv(pipe, Xtr, ytr, folds), **_cv_estratificado(pipe, Xtr, ytr)}
        run_id, m = _rodar(BASELINE, alvo, pipe, partes, _parametros(pipe), extras, {"etapa": "baseline"}, folds)
        run_h, m_h = _heuristica(alvo, partes, folds)
        # Primeira etapa do treino: estado novo, sem top2, otimizacao, escolhido e campeao do treino anterior.
        _estado(alvo, zerar=True, comparacao={BASELINE: {**m, **extras, "run_id": run_id}},
                heuristica={**m_h, "run_id": run_h})
        print(f"[{alvo}] baseline: CV temporal PR-AUC {extras['cv_temporal_pr_auc_mean']:.3f} "
              f"(estratificado {extras['cv_estratificado_pr_auc_mean']:.3f}), validação {m['pr_auc']:.3f}")
        print(f"[{alvo}] {HEURISTICA}: CV temporal PR-AUC {m_h['cv_temporal_pr_auc_mean']:.3f}, "
              f"validação {m_h['pr_auc']:.3f}")


def comparar_modelos(features: pd.DataFrame | None = None) -> dict:
    """Experimento 02: os cinco modelos, um run cada. Devolve os 2 melhores por alvo."""
    _mlflow()
    mlflow.set_experiment(EXPERIMENTOS["comparacao"])
    melhores = {}
    for alvo in ALVOS:
        feats, partes, folds = _dados(alvo, features)
        Xtr, ytr = _xy(partes["treino"], alvo)
        comparacao = _estado(alvo).get("comparacao", {})
        for nome in COMPARADOS:
            pipe = montar_pipeline(feats, nome)
            extras = {**_cv(pipe, Xtr, ytr, folds), **_cv_estratificado(pipe, Xtr, ytr)}
            run_id, m = _rodar(nome, alvo, pipe, partes, _parametros(pipe), extras, {"etapa": "comparacao"}, folds)
            comparacao[nome] = {**m, **extras, "run_id": run_id}
            print(f"[{alvo}] {nome}: CV temporal PR-AUC {extras['cv_temporal_pr_auc_mean']:.3f} "
                  f"(estratificado {extras['cv_estratificado_pr_auc_mean']:.3f}), validação {m['pr_auc']:.3f}")
        # Seleção pela CV temporal no treino: a validação fica para escolher entre os otimizados.
        ranking = sorted(comparacao, key=lambda n: comparacao[n]["cv_temporal_pr_auc_mean"], reverse=True)
        melhores[alvo] = ranking[:2]
        _estado(alvo, comparacao=comparacao, top2=ranking[:2])
    return melhores


def otimizar(features: pd.DataFrame | None = None) -> dict:
    """Experimento 03: Optuna (estratégia principal) e RandomizedSearchCV (referência) nos 2
    melhores, ambos com a validação temporal. Um run por trial."""
    _mlflow()
    mlflow.set_experiment(EXPERIMENTOS["otimizacao"])
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    escolhidos = {}
    for alvo in ALVOS:
        feats, partes, folds = _dados(alvo, features)
        Xtr, ytr = _xy(partes["treino"], alvo)
        resultado = {}
        for nome in _estado(alvo)["top2"]:
            def objetivo(trial, nome=nome):
                params = ESPACOS[nome](trial)
                pipe = montar_pipeline(feats, nome, **params)
                cv = _cv(pipe, Xtr, ytr, folds)
                run_id, m = _rodar(f"{nome}_optuna_{trial.number:02d}", alvo, pipe, partes, params, cv,
                                   {"etapa": "otimizacao", "busca": "optuna", "modelo": nome})
                trial.set_user_attr("params", params)
                trial.set_user_attr("run_id", run_id)
                trial.set_user_attr("validacao", m)
                return cv["cv_temporal_pr_auc_mean"]

            estudo = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEMENTE))
            estudo.optimize(objetivo, n_trials=N_TRIALS)
            melhor = estudo.best_trial

            sorteio = RandomizedSearchCV(montar_pipeline(feats, nome),
                                         {f"modelo__{k}": v for k, v in SORTEIOS[nome].items()},
                                         n_iter=N_SORTEIOS, cv=folds, scoring="average_precision",
                                         random_state=SEMENTE, refit=False).fit(Xtr, ytr)
            params_sorteio = {k.removeprefix("modelo__"): v for k, v in sorteio.best_params_.items()}
            cv_sorteio = _cv(montar_pipeline(feats, nome, **params_sorteio), Xtr, ytr, folds)
            _rodar(f"{nome}_randomized_search", alvo, montar_pipeline(feats, nome, **params_sorteio), partes,
                   params_sorteio, cv_sorteio, {"etapa": "otimizacao", "busca": "randomized_search", "modelo": nome})

            resultado[nome] = {"params": melhor.user_attrs["params"], "cv_temporal_pr_auc_mean": melhor.value,
                               "run_id": melhor.user_attrs["run_id"], "validacao": melhor.user_attrs["validacao"],
                               "randomized_search_cv_pr_auc": float(sorteio.best_score_)}
            print(f"[{alvo}] {nome}: Optuna CV {melhor.value:.3f} (validação "
                  f"{melhor.user_attrs['validacao']['pr_auc']:.3f}) | RandomizedSearch CV {sorteio.best_score_:.3f}")
        # Entre os dois otimizados, decide a validação de 2023, que nenhuma busca viu.
        escolhido = max(resultado, key=lambda n: resultado[n]["validacao"]["pr_auc"])
        escolhidos[alvo] = escolhido
        _estado(alvo, otimizacao=resultado, escolhido=escolhido)
    return escolhidos


def registrar_campeao(features: pd.DataFrame | None = None) -> dict:
    """Retreina o escolhido em treino + validação, mede no teste (2024) com o limiar escolhido
    na validação, calcula a importância por permutação e registra no Model Registry."""
    _mlflow()
    mlflow.set_experiment(EXPERIMENTOS["otimizacao"])
    cliente, registrados = MlflowClient(), {}
    for alvo in ALVOS:
        feats, partes, _ = _dados(alvo, features)
        estado = _estado(alvo)
        nome = estado["escolhido"]
        escolha = estado["otimizacao"][nome]
        limiar = escolha["validacao"]["limiar"]
        pipe = montar_pipeline(feats, nome, **escolha["params"])
        Xtv, ytv = _xy(pd.concat([partes["treino"], partes["validacao"]]), alvo)
        Xte, yte = _xy(partes["teste"], alvo)
        pipe.fit(Xtv, ytv)
        score = pipe.predict_proba(Xte)[:, 1]
        m = metricas.avaliar(yte, score, partes["teste"]["trimestre"], limiar)
        titulo = f"campeão {nome} | {alvo} | teste 2024"
        tabela = pd.DataFrame({**estado["comparacao"], HEURISTICA: estado["heuristica"]}).T
        # O ingênuo também no teste de 2024, com o limiar dele escolhido na validação.
        m_h = metricas.avaliar(yte, score_heuristica(partes["teste"]).to_numpy(), partes["teste"]["trimestre"],
                               estado["heuristica"]["limiar"])
        with mlflow.start_run(run_name=f"campeao_{nome}", tags={"alvo": alvo, "etapa": "campeao", "modelo": nome}) as run, \
                tempfile.TemporaryDirectory() as tmp:
            mlflow.log_params({**{k: str(v) for k, v in escolha["params"].items()}, "modelo": nome,
                               "treinado_em": "2021Q1-2023Q4", "limiar_escolhido_em": "validacao 2023"})
            mlflow.log_metrics({**{f"test_{k}": v for k, v in m.items()},
                                **{f"val_{k}": v for k, v in escolha["validacao"].items()},
                                "cv_temporal_pr_auc_mean": escolha["cv_temporal_pr_auc_mean"],
                                **{f"heuristica_test_{k}": m_h[k] for k in ("pr_auc", "recall_at_50", "recall_at_100")},
                                "ganho_test_pr_auc_sobre_heuristica": m["pr_auc"] - m_h["pr_auc"]})
            metricas.graficos(yte, score, limiar, Path(tmp), titulo)
            metricas.barras_comparacao(tabela, Path(tmp) / "comparacao_modelos.png", f"{alvo}: validação 2023")
            tabela.to_csv(Path(tmp) / "comparacao_modelos.csv")
            _, importancia = metricas.importancia_permutacao(pipe, Xte, yte, Path(tmp) / "importancia_permutacao.png",
                                                             titulo)
            importancia.to_csv(Path(tmp) / "importancia_permutacao.csv", header=["queda_pr_auc"])
            (Path(tmp) / "classification_report.txt").write_text(metricas.relatorio(yte, score, limiar), encoding="utf-8")
            mlflow.log_artifacts(tmp)
            info = mlflow.sklearn.log_model(pipe, name="modelo", input_example=Xtv.head(3),
                                            registered_model_name=NOME_REGISTRO[alvo], serialization_format=FORMATO)
        cliente.set_registered_model_alias(NOME_REGISTRO[alvo], ALIAS, info.registered_model_version)
        registrados[alvo] = {"nome": NOME_REGISTRO[alvo], "versao": info.registered_model_version,
                             "run_id": run.info.run_id, "modelo": nome, "teste": m}
        _estado(alvo, campeao=registrados[alvo])
        print(f"[{alvo}] campeão {nome} -> {NOME_REGISTRO[alvo]} v{info.registered_model_version} @{ALIAS}: "
              f"teste PR-AUC {m['pr_auc']:.3f} (prevalência {m['prevalencia']:.3f}), "
              f"recall@50 {m['recall_at_50']:.3f}, recall@100 {m['recall_at_100']:.3f} | "
              f"{HEURISTICA}: PR-AUC {m_h['pr_auc']:.3f}, recall@50 {m_h['recall_at_50']:.3f}")
    return registrados


if __name__ == "__main__":
    tabela = carregar_features()
    treinar_baseline(tabela)
    comparar_modelos(tabela)
    otimizar(tabela)
    registrar_campeao(tabela)
