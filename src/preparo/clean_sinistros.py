"""Cleans the CTTU sinistros CSVs (2015-2024) into one parquet in data/processed/sinistros/.

Normalizes column names/types across years, dates, horas, bairros and enderecos, and
derives atropelamento + vulnerable-user flags. Only exact duplicate rows are dropped, and
counted; every other anomaly becomes a flag column counted in the generated README.
"""
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "cttu" / "acidentes-de-transito-com-e-sem-vitimas"
OUT_DIR = ROOT / "data" / "processed" / "sinistros"

COUNT_COLS = ["auto", "moto", "ciclom", "ciclista", "pedestre", "onibus", "caminhao",
              "viatura", "outros", "vitimas", "vitimasfatais"]
CONTEXT_COLS = ["acidente_verificado", "tempo_clima", "situacao_semaforo", "sinalizacao",
                "condicao_via", "conservacao_via", "ponto_controle", "situacao_placa",
                "velocidade_max_via", "mao_direcao", "divisao_via1", "divisao_via2", "divisao_via3"]
TEXT_COLS = ["situacao", "endereco", "numero", "detalhe_endereco_acidente", "complemento",
             "endereco_cruzamento", "numero_cruzamento", "referencia_cruzamento",
             "bairro_cruzamento", "sentido_via", "descricao"]


def _unaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _clean_text(s: pd.Series) -> pd.Series:
    s = s.fillna("").str.upper().str.replace(r"\s+", " ", regex=True).str.strip()
    return s.replace("", pd.NA)


def _to_int(s: pd.Series) -> pd.Series:
    # 2022+ export numbers as "1,0"; earlier years as "1" or "".
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce").astype("Int64")


def criterio_atropelamento(tipo: pd.Series, pedestre: pd.Series) -> pd.Series:
    """'tipo+pedestre' | 'tipo' | 'pedestre' | None -- which rule makes the row a pedestrian collision.

    tipo: any ATROPELAMENTO variant except animal ones (ATROPELAMENTO, ATROPELAMENTO DE PESSOA;
    not ATROPELAMENTO [DE] ANIMAL). pedestre: participant count (> 0 = pedestrian involved).
    Informative only: the `atropelamento` flag stays the tipo-only rule.
    """
    tipo_norm = tipo.fillna("").map(lambda s: _unaccent(str(s)).upper())
    por_tipo = tipo_norm.str.contains("ATROPELAMENTO") & ~tipo_norm.str.contains("ANIMAL")
    por_pedestre = pd.to_numeric(pedestre, errors="coerce").fillna(0) > 0
    criterio = ["tipo+pedestre" if t and p else "tipo" if t else "pedestre" if p else None
                for t, p in zip(por_tipo, por_pedestre)]
    return pd.Series(criterio, index=tipo.index, dtype="object")


def load_year(csv_path: Path) -> tuple[int, pd.DataFrame]:
    return int(csv_path.stem[-4:]), pd.read_csv(csv_path, sep=";", dtype=str, keep_default_na=False)


def normalizar_schema(anos: dict[int, pd.DataFrame]) -> tuple[pd.DataFrame, dict[int, list[str]]]:
    """Unifies the yearly CSVs into one table; also returns the columns found in each year.

    Names become lowercase, unaccented, spaces -> '_', which maps DATA (2018-2019) to data.
    The portal's dictionary lists a `timestamp` column that exists in no CSV: the real name is
    data/DATA. A column missing in a year becomes null in that year's rows (e.g.
    endereco_cruzamento outside 2016-2019, acidente_verificado before 2018).
    """
    frames, colunas_por_ano = [], {}
    for ano, df in sorted(anos.items()):
        colunas_por_ano[ano] = list(df.columns)
        df = df.rename(columns=lambda c: re.sub(r"\s+", "_", _unaccent(c).strip()).lower())
        if ano == 2015:
            # Source anomaly (confirmed by inspection): 2015 'tipo' holds the severity and
            # 'natureza' the accident type -- the reverse of every other year.
            df = df.rename(columns={"tipo": "gravidade", "natureza": "tipo_acidente"})
        else:
            df = df.rename(columns={"natureza_acidente": "gravidade", "natureza": "gravidade",
                                    "tipo": "tipo_acidente"})
        frames.append(df.assign(ano_arquivo=ano))
    # concat aligns on the union of columns: one missing in a year is null for that year.
    return pd.concat(frames, ignore_index=True), colunas_por_ano


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=raw.index)
    out["ano_arquivo"] = raw["ano_arquivo"]
    out["protocolo"] = _to_int(raw["protocolo"]) if "protocolo" in raw else pd.NA  # only 2022+

    out["data"] = pd.to_datetime(raw["data"], format="%Y-%m-%d", errors="coerce")
    hora = raw["hora"].str.extract(r"^(\d{2}:\d{2}:\d{2})")[0]
    out["hora"] = pd.to_datetime(hora, format="%H:%M:%S", errors="coerce").dt.strftime("%H:%M:%S")
    out["datahora"] = pd.to_datetime(out["data"].dt.strftime("%Y-%m-%d") + " " + out["hora"], errors="coerce")
    out["hora_invalida"] = raw["hora"].ne("") & out["hora"].isna()
    out["data_fora_do_ano_arquivo"] = out["data"].dt.year != out["ano_arquivo"]

    out["gravidade"] = _clean_text(raw["gravidade"])
    out["tipo_acidente"] = _clean_text(raw["tipo_acidente"])

    # Bairro spelling varies by accent/spacing across years (POÇO/POCO DA PANELA, BOA  VIAGEM).
    # Group by unaccented key and keep the most frequent original spelling as canonical.
    bairro = _clean_text(raw["bairro"]).replace("0", pd.NA)
    key = bairro.dropna().map(_unaccent)
    canonical = bairro.dropna().groupby(key).agg(lambda s: s.value_counts().index[0])
    out["bairro"] = bairro.map(lambda b: canonical[_unaccent(b)] if pd.notna(b) else pd.NA)
    out["bairro_original"] = raw["bairro"].replace("", pd.NA)

    for col in TEXT_COLS:
        out[col] = _clean_text(raw[col]) if col in raw else pd.NA
    for col in ["numero", "numero_cruzamento"]:
        out[col] = out[col].str.replace(r",0$", "", regex=True).replace("0", pd.NA)
    out["num_semaforo"] = _to_int(raw["num_semaforo"]).replace(0, pd.NA) if "num_semaforo" in raw else pd.NA

    # Up to 2020 the source leaves the cell empty when the count is zero (no "0" is ever written
    # in those years); from 2021 zeros are explicit. So an empty cell is 0. Only a column missing
    # in a year (e.g. vitimasfatais in 2015) stays NA -- unknown, not zero.
    for col in COUNT_COLS:
        out[col] = _to_int(raw[col].replace("", "0")) if col in raw else pd.Series(pd.NA, index=raw.index, dtype="Int64")
    for col in CONTEXT_COLS:
        out[col] = raw[col].replace("", pd.NA) if col in raw else pd.NA
    # Exists only from 2018 on: filtering by it would drop 2015-2017, so it is a category instead.
    out["acidente_verificado"] = out["acidente_verificado"].fillna("DESCONHECIDO").astype("category")

    # 'ATROPELAMENTO' / 'ATROPELAMENTO DE PESSOA' (name changed in 2019); animals excluded.
    out["atropelamento"] = out["tipo_acidente"].str.startswith("ATROPELAMENTO", na=False) & \
        ~out["tipo_acidente"].str.contains("ANIMAL", na=False)
    out["criterio_atropelamento"] = criterio_atropelamento(out["tipo_acidente"], out["pedestre"])
    # Counts are participants by type, NOT victims -- the source doesn't say who got hurt.
    out["envolve_pedestre"] = out["pedestre"].fillna(0) > 0
    out["envolve_ciclista"] = (out["ciclista"].fillna(0) > 0) | out["tipo_acidente"].eq("COLISÃO COM CICLISTA")
    out["envolve_moto"] = (out["moto"].fillna(0) + out["ciclom"].fillna(0)) > 0
    # One label per sinistro, most vulnerable participant wins (pedestre > ciclista > moto).
    out["usuario_vulneravel"] = pd.Series(pd.NA, index=out.index, dtype="string")
    for flag, label in [("envolve_moto", "moto"), ("envolve_ciclista", "ciclista"), ("envolve_pedestre", "pedestre")]:
        out.loc[out[flag], "usuario_vulneravel"] = label
    out.loc[out["atropelamento"] & out["usuario_vulneravel"].isna(), "usuario_vulneravel"] = "pedestre"
    out["usuario_vulneravel"] = out["usuario_vulneravel"].fillna("nenhum")
    return out


def readme(df: pd.DataFrame, duplicados: pd.Series) -> str:
    por_ano = df.groupby("ano_arquivo").agg(
        sinistros=("ano_arquivo", "size"),
        atropelamentos=("atropelamento", "sum"),
        tipo_ou_pedestre=("criterio_atropelamento", "count"),
        com_pedestre=("envolve_pedestre", "sum"),
        com_ciclista=("envolve_ciclista", "sum"),
        com_moto=("envolve_moto", "sum"),
        vitimas_fatais=("vitimasfatais", lambda s: s.sum() if s.notna().any() else pd.NA),
    )
    preenchido = df[CONTEXT_COLS].notna()
    preenchido["acidente_verificado"] = df["acidente_verificado"].ne("DESCONHECIDO")
    vazios = preenchido.groupby(df["ano_arquivo"]).mean().mul(100).round(0).astype(int)
    return f"""# Sinistros de trânsito do Recife 2015–2024 (processado)

Gerado por `src/preparo/clean_sinistros.py` a partir de `data/raw/cttu/acidentes-de-transito-com-e-sem-vitimas/`
(Portal de Dados Abertos do Recife, CKAN, licença ODbL). Uma linha por **chamado** de sinistro.

## Ressalvas (não remover)

1. **2015 só tem dados a partir de junho** — total anual de 2015 está subestimado.
2. **São "chamados" da CTTU, não os registros estatísticos dos Relatórios Anuais** — os números
   podem divergir dos oficiais do PSVR. Nunca rotular somas daqui como "número oficial".
3. **2025 é preliminar.** O arquivo de 2024 traz {int(df['data_fora_do_ano_arquivo'].sum())} linhas datadas
   de dez/2025 (`data_fora_do_ano_arquivo=True`) — não corrigido; pode ser erro de digitação do ano.
4. **Colunas de veículo (`auto`, `moto`, `pedestre`...) contam participantes, não vítimas.**
   `usuario_vulneravel` diz quem estava envolvido, não quem se feriu. Prioridade: pedestre > ciclista > moto
   (`moto` inclui `ciclom`/ciclomotor). Atropelamento sem pedestre contado é rotulado `pedestre`.
5. **Cobertura cai muito a partir de 2020** (e "SEM VÍTIMA" quase some em 2021) — provável mudança no
   processo de registro, não queda real de sinistros. Comparar anos com cuidado.
6. **`vitimasfatais` não existe em 2015** → NA (desconhecido), nunca zero.
7. **2015 tem `tipo`/`natureza` trocadas na fonte** — destrocado aqui (`gravidade`, `tipo_acidente`).
8. `tipo_acidente` muda de vocabulário em 2019 (ex.: `ATROPELAMENTO` → `ATROPELAMENTO DE PESSOA`,
   `COLISÃO` → `COLISÃO TRASEIRA/LATERAL/...`). `atropelamento` cobre os dois.
9. `criterio_atropelamento` (`tipo+pedestre`, `tipo`, `pedestre` ou vazio) diz por qual regra a linha
   seria atropelamento; `atropelamento` continua sendo só a regra do `tipo`. Contagem:
   {df['criterio_atropelamento'].value_counts().to_dict()}. Quem quiser incluir os casos só com pedestre
   contado (`pedestre`, ex.: `COLISÃO` com pedestre) usa `criterio_atropelamento.notna()` e diz que fez.
10. `situacao` inclui `CANCELADA` e `DUPLICIDADE` — mantidas; decidir na análise se entram na contagem.
11. Sem lat/long na fonte e sem geocodificação (ARCHITECTURE.md, seção 2.3): o local é só texto.
12. Colunas de contexto (`tempo_clima`, `sinalizacao`...) só são preenchidas de 2018 a 2022 (vazias em 2023–2024, apesar de a coluna existir) e têm preenchimento
    irregular (tabela abaixo) — mudança de formulário, não necessariamente dado faltante.
13. **`hora` está vazia em todo o arquivo de 2022** e não é recuperável: `data` não traz horário e
    nenhuma outra coluna traz a hora.
14. **`acidente_verificado` só existe de 2018 em diante.** Não é usada como filtro (isso descartaria
    2015–2017); é categórica, com `DESCONHECIDO` onde não existe ou está vazia.
15. `endereco_cruzamento`, `numero_cruzamento` e `referencia_cruzamento` só existem de 2016 a 2019.
16. **Até 2020 a fonte deixa vazia a célula de contagem que vale zero** (`auto`, `moto`, `pedestre`,
    `vitimasfatais`...): nesses anos nenhum "0" é escrito. A partir de 2021 os zeros vêm explícitos.
    Aqui, célula vazia vira 0; só a coluna que não existe no ano (`vitimasfatais` em 2015) fica NA.

## Normalização aplicada

- `normalizar_schema`: nomes de coluna em minúsculas, sem acento e sem espaço (`DATA`→`data`; a
  coluna `timestamp` do dicionário do portal não existe nos CSVs); coluna ausente num ano vira nulo.
  Colunas encontradas em cada arquivo: `colunas_por_ano.json`.
- `natureza_acidente`/`natureza`→`gravidade`, `tipo`→`tipo_acidente` (trocadas em 2015, ver item 7).
- Duplicados exatos (linha idêntica em todas as colunas do mesmo arquivo) removidos:
  {int(duplicados.sum())} no total, por ano {duplicados[duplicados > 0].to_dict()}.
- `data` → datetime; `hora` → `HH:MM:SS` (milissegundos de 2015 removidos); texto inválido em `hora`
  vira NA com `hora_invalida=True` ({int(df['hora_invalida'].sum())} linhas). Hora vazia: {int(df['hora'].isna().sum() - df['hora_invalida'].sum())} linhas.
- Números `"1,0"` → inteiro (nullable).
- Texto: maiúsculas, espaços colapsados. `bairro`: grafias que só diferem em acento/espaço unificadas
  na grafia mais frequente (original em `bairro_original`). Erros de digitação (ex.: `IPESEP`) **não** corrigidos.

## Contagens por ano (arquivo de origem)

```
{por_ano.to_string()}
```

## % de preenchimento das colunas de contexto

```
{vazios.to_string()}
```
"""


NORMALIZADO = OUT_DIR / "normalizado.parquet"


def etapa_normalizar_schema() -> dict:
    """Tarefa normalizar_schema da DAG: unifica os CSVs e salva o log de colunas por ano."""
    csvs = sorted(RAW_DIR.glob("*.csv"))
    assert csvs, f"no CSV in {RAW_DIR} -- run python -m src.ingestao.fetch_datasets first"
    raw, colunas_por_ano = normalizar_schema(dict(load_year(p) for p in csvs))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_parquet(NORMALIZADO, index=False)
    (OUT_DIR / "colunas_por_ano.json").write_text(
        json.dumps(colunas_por_ano, ensure_ascii=False, indent=2), encoding="utf-8")
    return colunas_por_ano


def etapa_limpar() -> int:
    """Tarefa limpar da DAG: duplicados exatos, tipos e flags; grava o Parquet limpo e o README."""
    raw = pd.read_parquet(NORMALIZADO)
    duplicado = raw.duplicated()
    duplicados = duplicado.groupby(raw["ano_arquivo"]).sum()
    raw = raw[~duplicado].reset_index(drop=True)
    df = clean(raw)
    assert len(df) == len(raw), "clean() may not drop rows"
    assert df["gravidade"].isin(["SEM VÍTIMA", "COM VÍTIMA", "VÍTIMA FATAL"]).mean() > 0.99, "gravidade/tipo swap broke"
    assert df["data"].notna().all()
    df.to_parquet(OUT_DIR / "sinistros_2015_2024.parquet", index=False)
    (OUT_DIR / "README.md").write_text(readme(df, duplicados), encoding="utf-8")
    print(f"wrote {len(df)} rows to {OUT_DIR} ({int(duplicados.sum())} exact duplicates removed)")
    return len(df)


if __name__ == "__main__":
    etapa_normalizar_schema()
    etapa_limpar()
