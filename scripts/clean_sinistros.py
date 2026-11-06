"""Cleans the CTTU sinistros CSVs (2015-2024) into one parquet in data/processed/sinistros/.

Normalizes column names/types across years, dates, horas, bairros and enderecos, and
derives atropelamento + vulnerable-user flags. Never drops or "fixes" rows silently:
anomalies become flag columns and are counted in the generated README (docs/06).
"""
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "cttu" / "acidentes-de-transito-com-e-sem-vitimas"
OUT_DIR = ROOT / "data" / "processed" / "sinistros"

COUNT_COLS = ["auto", "moto", "ciclom", "ciclista", "pedestre", "onibus", "caminhao",
              "viatura", "outros", "vitimas", "vitimasfatais"]
CONTEXT_COLS = ["acidente_verificado", "tempo_clima", "situacao_semaforo", "sinalizacao",
                "condicao_via", "conservacao_via", "ponto_controle", "situacao_placa",
                "velocidade_max_via", "mao_direcao", "divisao_via1", "divisao_via2", "divisao_via3"]
TEXT_COLS = ["situacao", "endereco", "numero", "detalhe_endereco_acidente", "complemento",
             "bairro_cruzamento", "sentido_via", "descricao"]


def _unaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _clean_text(s: pd.Series) -> pd.Series:
    s = s.fillna("").str.upper().str.replace(r"\s+", " ", regex=True).str.strip()
    return s.replace("", pd.NA)


def _to_int(s: pd.Series) -> pd.Series:
    # 2022+ export numbers as "1,0"; earlier years as "1" or "".
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce").astype("Int64")


def load_year(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=";", dtype=str, keep_default_na=False)
    df.columns = df.columns.str.lower()
    ano_arquivo = int(csv_path.stem[-4:])
    if ano_arquivo == 2015:
        # Source anomaly (confirmed by inspection): 2015 'tipo' holds the severity and
        # 'natureza' the accident type -- the reverse of every other year.
        df = df.rename(columns={"tipo": "gravidade", "natureza": "tipo_acidente"})
    else:
        df = df.rename(columns={"natureza_acidente": "gravidade", "natureza": "gravidade",
                                "tipo": "tipo_acidente"})
    df["ano_arquivo"] = ano_arquivo
    return df


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
    out["numero"] = out["numero"].str.replace(r",0$", "", regex=True).replace("0", pd.NA)
    out["num_semaforo"] = _to_int(raw["num_semaforo"]).replace(0, pd.NA) if "num_semaforo" in raw else pd.NA

    # A column missing in a year (e.g. vitimasfatais in 2015) stays NA -- unknown, not zero.
    for col in COUNT_COLS:
        out[col] = _to_int(raw[col]) if col in raw else pd.Series(pd.NA, index=raw.index, dtype="Int64")
    for col in CONTEXT_COLS:
        out[col] = raw[col].replace("", pd.NA) if col in raw else pd.NA

    # 'ATROPELAMENTO' / 'ATROPELAMENTO DE PESSOA' (name changed in 2019); animals excluded.
    out["atropelamento"] = out["tipo_acidente"].str.startswith("ATROPELAMENTO", na=False) & \
        ~out["tipo_acidente"].str.contains("ANIMAL", na=False)
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


def readme(df: pd.DataFrame) -> str:
    por_ano = df.groupby("ano_arquivo").agg(
        sinistros=("ano_arquivo", "size"),
        atropelamentos=("atropelamento", "sum"),
        com_pedestre=("envolve_pedestre", "sum"),
        com_ciclista=("envolve_ciclista", "sum"),
        com_moto=("envolve_moto", "sum"),
        vitimas_fatais=("vitimasfatais", lambda s: s.sum() if s.notna().any() else pd.NA),
    )
    vazios = df[CONTEXT_COLS].notna().groupby(df["ano_arquivo"]).mean().mul(100).round(0).astype(int)
    return f"""# Sinistros de trânsito do Recife 2015–2024 (processado)

Gerado por `scripts/clean_sinistros.py` a partir de `data/raw/cttu/acidentes-de-transito-com-e-sem-vitimas/`
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
9. `situacao` inclui `CANCELADA` e `DUPLICIDADE` — mantidas; decidir na análise se entram na contagem.
10. Sem lat/long na fonte — ver `geocode_sinistros.py` e a coluna de precisão antes de análise espacial.
11. Colunas de contexto (`tempo_clima`, `sinalizacao`...) só são preenchidas de 2018 a 2022 (vazias em 2023–2024, apesar de a coluna existir) e têm preenchimento
    irregular (tabela abaixo) — mudança de formulário, não necessariamente dado faltante.

## Normalização aplicada

- Nomes de coluna unificados entre anos (`DATA`→`data`, `natureza_acidente`/`natureza`→`gravidade`).
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


if __name__ == "__main__":
    raw = pd.concat([load_year(p) for p in sorted(RAW_DIR.glob("*.csv"))], ignore_index=True)
    df = clean(raw)
    assert len(df) == len(raw), "no row may be dropped"
    assert df["gravidade"].isin(["SEM VÍTIMA", "COM VÍTIMA", "VÍTIMA FATAL"]).mean() > 0.99, "gravidade/tipo swap broke"
    assert df["data"].notna().all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_DIR / "sinistros_2015_2024.parquet", index=False)
    (OUT_DIR / "README.md").write_text(readme(df), encoding="utf-8")
    print(f"wrote {len(df)} rows to {OUT_DIR}")
