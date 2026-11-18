"""Constrói o local_id, o trimestre e a tabela dim_local a partir dos sinistros limpos.

ARCHITECTURE.md, seção 3.1. O local é só texto (bairro + logradouro normalizados), estável nos
10 anos; hora e cruzamento não entram na chave. Saídas em data/processed/:
- acidentes_local.parquet: um acidente por linha, com local_id e trimestre, já sem o que não
  conta como acidente
- dim_local.parquet (e tabela dim_local no Postgres): chave, bairro e logradouro legíveis
- local_id_resumo.json: exclusões, nº de locais e distribuição de acidentes por local
"""
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from unidecode import unidecode

ROOT = Path(__file__).resolve().parents[2]
ENTRADA = ROOT / "data" / "processed" / "sinistros" / "sinistros_2015_2024.parquet"
SAIDA = ROOT / "data" / "processed"

PREFIXOS = {"RUA", "R", "AV", "AVENIDA", "TRAVESSA", "TV", "ESTRADA", "ESTR", "PRACA", "PCA"}
# Chamado cancelado e chamado repetido não são acidentes a mais: ficam no Parquet limpo, fora das contagens.
SITUACOES_EXCLUIDAS = {"CANCELADA", "DUPLICIDADE"}


def normalizar_texto(s: pd.Series) -> pd.Series:
    """Maiúsculas, sem acento, sem pontuação e com espaços colapsados; vazio vira nulo."""
    t = s.astype("object").map(lambda v: re.sub(r"[^A-Z0-9]+", " ", unidecode(v).upper()).strip(),
                               na_action="ignore")
    return t.replace("", pd.NA)


def normalizar_logradouro(s: pd.Series) -> pd.Series:
    """normalizar_texto e, além disso, sem o prefixo do tipo de via (RUA, AV, TRAVESSA...)."""
    t = normalizar_texto(s).map(
        lambda v: " ".join(v.split()[1:]) if v.split()[0] in PREFIXOS else v, na_action="ignore")
    return t.replace("", pd.NA)


def gerar_local_id(bairro_norm: pd.Series, logradouro_norm: pd.Series) -> pd.Series:
    """sha1(bairro|logradouro)[:12]; nulo quando falta bairro ou logradouro."""
    chave = bairro_norm + "|" + logradouro_norm
    return chave.map(lambda k: hashlib.sha1(k.encode()).hexdigest()[:12], na_action="ignore")


def preparar_acidentes(sinistros: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Tira o que não conta como acidente e acrescenta local_id, trimestre e as marcas de vítima."""
    excluidas = sinistros["situacao"].isin(SITUACOES_EXCLUIDAS)
    # Linhas do arquivo de 2024 datadas de dez/2025: criariam trimestres vazios em 2025 e um alvo
    # falso para 2024Q4.
    fora_do_ano = sinistros["data_fora_do_ano_arquivo"].fillna(False) & ~excluidas
    acidentes = sinistros[~excluidas & ~fora_do_ano].copy()

    acidentes["bairro_norm"] = normalizar_texto(acidentes["bairro"])
    acidentes["logradouro_norm"] = normalizar_logradouro(acidentes["endereco"])
    acidentes["local_id"] = gerar_local_id(acidentes["bairro_norm"], acidentes["logradouro_norm"])
    acidentes["trimestre"] = acidentes["data"].dt.to_period("Q").astype(str)
    acidentes["com_vitima"] = (acidentes["vitimas"].fillna(0) > 0) | (acidentes["vitimasfatais"].fillna(0) > 0)
    # vitimasfatais não existe em 2015: lá, fatal fica False (2015 só entra como histórico).
    acidentes["fatal"] = acidentes["vitimasfatais"].fillna(0) > 0

    exclusoes = {
        "situacao_excluida": sinistros.loc[excluidas, "situacao"].value_counts().to_dict(),
        "data_fora_do_ano_arquivo": int(fora_do_ano.sum()),
        "sem_bairro_ou_logradouro": int(acidentes["local_id"].isna().sum()),
    }
    return acidentes.reset_index(drop=True), exclusoes


def construir_dim_local(acidentes: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por local_id, com a grafia mais frequente do bairro e do logradouro."""
    com_local = acidentes.dropna(subset=["local_id"])
    mais_frequente = lambda s: s.value_counts().index[0] if s.notna().any() else pd.NA
    return (com_local.groupby("local_id")
            .agg(bairro=("bairro", mais_frequente), logradouro=("endereco", mais_frequente),
                 bairro_norm=("bairro_norm", "first"), logradouro_norm=("logradouro_norm", "first"),
                 n_acidentes=("local_id", "size"))
            .reset_index())


def resumo(acidentes: pd.DataFrame, dim_local: pd.DataFrame, exclusoes: dict) -> dict:
    por_local = dim_local["n_acidentes"]
    return {
        "acidentes": len(acidentes),
        "acidentes_com_local_id": int(acidentes["local_id"].notna().sum()),
        "exclusoes": exclusoes,
        "locais_distintos": len(dim_local),
        "locais_com_3_ou_mais_acidentes": int((por_local >= 3).sum()),
        "acidentes_por_local": {k: round(float(v), 2) for k, v in por_local.describe(
            percentiles=[.25, .5, .75, .9, .99]).items()},
        "locais_por_faixa_de_acidentes": por_local.pipe(
            pd.cut, [0, 1, 2, 5, 10, 50, float("inf")], labels=["1", "2", "3-5", "6-10", "11-50", "51+"]
        ).value_counts(sort=False).to_dict(),
    }


def indicadores_ano(acidentes: pd.DataFrame) -> pd.DataFrame:
    """Indicadores do Projeto 6 por ano, para a aba 1 do dashboard (ARCHITECTURE.md, seção 17.6):
    volume, vítimas, atropelamentos com vítima e usuários vulneráveis envolvidos."""
    ano = acidentes["data"].dt.year.rename("ano")
    atropelamento = (acidentes["pedestre"].fillna(0) > 0) & acidentes["com_vitima"]
    return pd.DataFrame({
        "acidentes": acidentes.groupby(ano).size(),
        "acidentes_com_vitima": acidentes["com_vitima"].groupby(ano).sum(),
        "vitimas": acidentes["vitimas"].fillna(0).groupby(ano).sum(),
        "vitimas_fatais": acidentes["vitimasfatais"].fillna(0).groupby(ano).sum(),
        "atropelamentos_com_vitima": atropelamento.groupby(ano).sum(),
        "com_pedestre": acidentes["envolve_pedestre"].groupby(ano).sum(),
        "com_ciclista": acidentes["envolve_ciclista"].groupby(ano).sum(),
        "com_moto": acidentes["envolve_moto"].groupby(ano).sum(),
    }).astype("int64").reset_index()


def executar() -> dict:
    """Tarefa construir_local_id da DAG: grava acidentes com local, dim_local e indicadores."""
    from src.comum.db import engine

    acidentes, exclusoes = preparar_acidentes(pd.read_parquet(ENTRADA))
    dim_local = construir_dim_local(acidentes)
    info = resumo(acidentes, dim_local, exclusoes)
    assert dim_local["local_id"].is_unique

    acidentes.to_parquet(SAIDA / "acidentes_local.parquet", index=False)
    dim_local.to_parquet(SAIDA / "dim_local.parquet", index=False)
    (SAIDA / "local_id_resumo.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    dim_local.to_sql("dim_local", engine(), if_exists="replace", index=False)
    indicadores_ano(acidentes).to_sql("indicadores_ano", engine(), if_exists="replace", index=False)
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return info


if __name__ == "__main__":
    executar()
