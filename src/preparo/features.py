"""Monta a tabela de features local_id × trimestre (ARCHITECTURE.md, seções 3.1 a 3.3).

Cada linha (local, t) usa só acidentes até o trimestre t; os dois alvos olham o trimestre t+1:
y_vitima (acidente com vítima) e y_atropelamento (acidente com pedestre e vítima).
tests/test_features.py tem o teste de não-vazamento que garante isso. Entrada:
data/processed/acidentes_local.parquet (de src.preparo.local_id). Saída:
data/processed/features.parquet, a tabela features no Postgres e
data/processed/positivos_por_trimestre.csv (positivos de cada alvo por trimestre).

Os agregados por (local, trimestre) entram num painel completo (todo local da grade × todo
trimestre da série), e as features saem só de operações que olham para trás: janela móvel,
soma acumulada, preenchimento para a frente e moda sobre contagens acumuladas.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.modelagem.validacao import PERIODOS
from src.preparo.local_id import normalizar_logradouro, normalizar_texto

ROOT = Path(__file__).resolve().parents[2]
ENTRADA = ROOT / "data" / "processed" / "acidentes_local.parquet"
SAIDA = ROOT / "data" / "processed" / "features.parquet"
POSITIVOS = ROOT / "data" / "processed" / "positivos_por_trimestre.csv"
ALVOS = ["y_vitima", "y_atropelamento"]

MINIMO_ACIDENTES_GRADE = 3
# A grade conta só acidentes até o fim do treino: contar a série inteira poria no treino locais
# escolhidos por acidentes de 2023-2024 (ARCHITECTURE.md, seção 17.7).
FIM_GRADE = PERIODOS["treino"][1]
JANELAS = (1, 2, 4)
PERIODOS = {"madrugada": (0, 5), "manha": (6, 11), "tarde": (12, 17), "noite": (18, 23)}
ENVOLVIDOS = ["auto", "moto", "ciclom", "ciclista", "pedestre", "onibus", "caminhao"]
VIA_CATEGORICAS = ["sinalizacao", "condicao_via", "conservacao_via", "situacao_semaforo", "mao_direcao",
                   "sentido_via", "ponto_controle", "situacao_placa", "divisao_via1", "acidente_verificado"]
TELEMETRIA = {"tel_velocidade_media": ("velocidade_kmh", "mean"), "tel_velocidade_max": ("velocidade_kmh", "max"),
              "tel_passagens": ("velocidade_kmh", "size"), "tel_frenagens": ("frenagem_brusca", "sum")}
MODAS = {"tempo_clima": "tempo_clima_mais_frequente",
         # natureza_acidente é a gravidade (COM VÍTIMA, SEM VÍTIMA...); no Parquet limpo ela se chama gravidade.
         "gravidade": "natureza_acidente_mais_frequente"}


def selecionar_grade(acidentes: pd.DataFrame, minimo: int = MINIMO_ACIDENTES_GRADE,
                     ate: str | None = FIM_GRADE) -> list[str]:
    """Locais com pelo menos `minimo` acidentes até o trimestre `ate`, inclusive (seção 3.1).
    `ate=None` conta a série inteira."""
    if ate is not None:
        tri = pd.PeriodIndex(acidentes["trimestre"], freq="Q")
        acidentes = acidentes[tri <= pd.Period(ate, freq="Q")]
    n = acidentes["local_id"].value_counts()
    return sorted(n[n >= minimo].index)


def _contagens(acc: pd.DataFrame) -> pd.DataFrame:
    """Uma coluna numérica por coisa a somar, uma linha por acidente."""
    # astype("string"): um recorte só com hora vazia (como 2022) chega aqui como float.
    hora = pd.to_numeric(acc["hora"].astype("string").str[:2], errors="coerce").astype("float64")
    return pd.DataFrame({
        "n": 1,
        "n_vit": acc["com_vitima"].astype(int),
        "n_atrop": ((acc["pedestre"].fillna(0) > 0) & acc["com_vitima"]).astype(int),
        "n_fatal": acc["fatal"].astype(int),
        "n_hora": hora.notna().astype(int),
        **{f"n_{p}": hora.between(ini, fim).astype(int) for p, (ini, fim) in PERIODOS.items()},
        "n_fds": (acc["data"].dt.day_of_week >= 5).astype(int),
        "n_cruz": acc["endereco_cruzamento"].notna().astype(int),
        "n_semaforo": acc["num_semaforo"].notna().astype(int),
        **{f"soma_{c}": acc[c].astype("float64") for c in ENVOLVIDOS},
        **{f"cont_{c}": acc[c].notna().astype(int) for c in ENVOLVIDOS},
    }, index=acc.index)


def _janela(serie: pd.Series, w: int) -> pd.Series:
    """Soma dos últimos w trimestres, incluindo o atual, dentro de cada local."""
    return serie.groupby(level="local_id").transform(lambda s: s.rolling(w, min_periods=1).sum())


def montar_features(acidentes: pd.DataFrame, locais: list[str],
                    telemetria: pd.DataFrame | None = None) -> pd.DataFrame:
    acc = acidentes.assign(tri=pd.PeriodIndex(acidentes["trimestre"], freq="Q")).sort_values("data", kind="stable")
    trimestres = pd.period_range(acc["tri"].min(), acc["tri"].max(), freq="Q")
    painel = pd.MultiIndex.from_product([locais, trimestres], names=["local_id", "tri"])
    no_local = acc[acc["local_id"].isin(locais)]
    tri_da_linha = painel.get_level_values("tri")

    soma = (_contagens(no_local).groupby([no_local["local_id"], no_local["tri"]]).sum()
            .reindex(painel, fill_value=0).astype("float64"))
    acum = soma.groupby(level="local_id").cumsum()
    f = pd.DataFrame(index=painel)

    # Histórico no local, em contagem absoluta e em participação nos acidentes da cidade (seção 3.2).
    cidade = _contagens(acc).groupby(acc["tri"])[["n", "n_vit", "n_fatal"]].sum().reindex(trimestres, fill_value=0)
    recortes = [("acidentes", "n", w) for w in JANELAS] + [("acidentes_vitima", "n_vit", w) for w in JANELAS]
    recortes.append(("acidentes_fatal", "n_fatal", 4))
    for nome, col, w in recortes:
        f[f"{nome}_{w}t"] = _janela(soma[col], w)
        total = cidade[col].rolling(w, min_periods=1).sum().replace(0, np.nan)
        f[f"rel_{nome}_{w}t"] = f[f"{nome}_{w}t"] / total.reindex(tri_da_linha).to_numpy()

    teve = soma["n"] > 0
    sequencia = (~teve).groupby(level="local_id").cumsum()
    f["trimestres_consecutivos_com_acidente"] = teve.astype(int).groupby(
        [painel.get_level_values("local_id"), sequencia]).cumsum()
    ordem = pd.Series(np.tile(np.arange(len(trimestres)), len(locais)), index=painel, dtype="float64")
    ultimo_com_vitima = ordem.where(soma["n_vit"] > 0).groupby(level="local_id").ffill()
    f["trimestres_desde_acidente_vitima"] = ordem - ultimo_com_vitima  # nulo se nunca houve

    # Perfil horário: só das linhas com hora (vazia em todo 2022).
    for p in PERIODOS:
        f[f"frac_{p}"] = acum[f"n_{p}"] / acum["n_hora"].replace(0, np.nan)
    f["hora_indisponivel"] = acum["n_hora"] == 0
    f["frac_fim_de_semana"] = acum["n_fds"] / acum["n"].replace(0, np.nan)

    # Cruzamento: endereco_cruzamento só existe em 2016-2019.
    f["tem_cruzamento_registrado"] = acum["n_cruz"] > 0
    transversais = no_local.assign(via=normalizar_logradouro(no_local["endereco_cruzamento"])).dropna(subset=["via"])
    primeira_vez = transversais.groupby(["local_id", "via"])["tri"].min().reset_index()
    f["n_vias_transversais"] = (primeira_vez.groupby(["local_id", "tri"]).size()
                                .reindex(painel, fill_value=0).groupby(level="local_id").cumsum())

    for c in ENVOLVIDOS:
        f[f"media_{c}"] = acum[f"soma_{c}"] / acum[f"cont_{c}"].replace(0, np.nan)

    # Via: último valor conhecido até t.
    via = pd.DataFrame({
        "velocidade_max_via": pd.to_numeric(no_local["velocidade_max_via"].astype("string")
                                            .str.extract(r"(\d+)", expand=False), errors="coerce"),
        **{c: normalizar_texto(no_local[c]) for c in VIA_CATEGORICAS},
    }, index=no_local.index)
    via["acidente_verificado"] = via["acidente_verificado"].mask(via["acidente_verificado"] == "DESCONHECIDO")
    ultimo = (via.groupby([no_local["local_id"], no_local["tri"]]).last()
              .reindex(painel).groupby(level="local_id").ffill())
    for c in via:
        f[c] = ultimo[c]
    f["tem_semaforo"] = acum["n_semaforo"] > 0

    # Contexto: categoria mais frequente até t (empate: a primeira em ordem alfabética).
    for col, nome in MODAS.items():
        valor = normalizar_texto(no_local[col])
        cont = (pd.crosstab([no_local["local_id"], no_local["tri"]], valor)
                .reindex(painel, fill_value=0).groupby(level="local_id").cumsum())
        f[nome] = cont.idxmax(axis=1).where(cont.sum(axis=1) > 0) if cont.shape[1] else np.nan

    # Bairro: a categórica e os acidentes do bairro inteiro no trimestre t.
    bairro_do_local = acc.dropna(subset=["local_id"]).groupby("local_id")["bairro_norm"].first()
    f["bairro"] = bairro_do_local.reindex(painel.get_level_values("local_id")).to_numpy()
    por_bairro = acc.groupby(["bairro_norm", "tri"]).size()
    f["acidentes_bairro_1t"] = por_bairro.reindex(
        pd.MultiIndex.from_arrays([f["bairro"], tri_da_linha])).fillna(0).to_numpy()

    # Telemetria do ESP32/simulador no trimestre da linha; nula onde não houve passagem. Não entra
    # no modelo desta fase: não cobre nenhum trimestre de treino (ARCHITECTURE.md, seção 17.4).
    if telemetria is not None and len(telemetria):
        tri_tel = pd.to_datetime(telemetria["momento"], utc=True).dt.tz_convert(None).dt.to_period("Q")
        agregado = telemetria.groupby([telemetria["local_id"], tri_tel.rename("tri")]).agg(**TELEMETRIA)
        agregado.index = agregado.index.set_names(["local_id", "tri"])
        agregado = agregado.reindex(painel)
    else:
        agregado = pd.DataFrame(np.nan, index=painel, columns=list(TELEMETRIA))
    for c in TELEMETRIA:
        f[c] = agregado[c].astype("float64")

    f["ano"] = tri_da_linha.year
    f["trimestre_do_ano"] = tri_da_linha.quarter
    f["periodo_pandemia"] = tri_da_linha.year.isin([2020, 2021])

    # Alvos: houve, no trimestre seguinte, acidente com vítima / atropelamento com vítima?
    # Nulos no último trimestre da série, que é a linha de scoring.
    for alvo, col in zip(ALVOS, ["n_vit", "n_atrop"]):
        proximo = soma[col].groupby(level="local_id").shift(-1)
        f[alvo] = (proximo > 0).astype("Int8").mask(proximo.isna())

    contagens = [f"{nome}_{w}t" for nome, _, w in recortes] + [
        "acidentes_bairro_1t", "trimestres_consecutivos_com_acidente", "n_vias_transversais"]
    f[contagens] = f[contagens].astype("int64")
    f = f.reset_index()
    f.insert(1, "trimestre", f.pop("tri").astype(str))
    return f


def positivos_por_trimestre(features: pd.DataFrame) -> pd.DataFrame:
    """Linhas, positivos e prevalência de cada alvo por trimestre (linhas com alvo conhecido)."""
    rotulado = features.dropna(subset=ALVOS)
    por_tri = rotulado.groupby("trimestre")[ALVOS].agg(["sum", "mean"])
    por_tri.columns = [f"{alvo}_{'positivos' if m == 'sum' else 'prevalencia'}" for alvo, m in por_tri.columns]
    return por_tri.assign(linhas=rotulado.groupby("trimestre").size()).reset_index()


def executar() -> pd.DataFrame:
    """Monta, valida e grava as features; usado pela DAG e pela linha de comando."""
    from src.comum.db import engine

    from sqlalchemy import inspect

    acidentes = pd.read_parquet(ENTRADA)
    locais = selecionar_grade(acidentes)
    banco = engine()
    # A tabela telemetria nasce com o ingestor (etapa 7); antes dele, as colunas tel_* ficam nulas.
    telemetria = pd.read_sql_table("telemetria", banco) if inspect(banco).has_table("telemetria") else None
    features = montar_features(acidentes, locais, telemetria)
    assert not features.duplicated(["local_id", "trimestre"]).any()

    features.to_parquet(SAIDA, index=False)
    features.to_sql("features", banco, if_exists="replace", index=False, chunksize=10_000)
    positivos = positivos_por_trimestre(features)
    positivos.to_csv(POSITIVOS, index=False)
    print(f"grade: {len(locais)} locais com >= {MINIMO_ACIDENTES_GRADE} acidentes até {FIM_GRADE}")
    print(f"features: {len(features)} linhas x {features.shape[1]} colunas, "
          f"{features['trimestre'].min()} a {features['trimestre'].max()}")
    print(positivos[positivos["trimestre"] >= "2021Q1"].round(3).to_string(index=False))
    return features


if __name__ == "__main__":
    executar()
