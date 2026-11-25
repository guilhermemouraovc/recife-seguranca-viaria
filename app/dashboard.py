"""Dashboard Streamlit da solução (ARCHITECTURE.md, seção 11).

Consome a API (ranking, detalhe, métricas, modelo, indicadores) e o MQTT (telemetria, status dos
serviços e aviso de scores novos). A aba de métricas lê os gráficos e a comparação entre modelos
direto do MLflow; a de saúde consulta a API do Airflow para a última execução de cada DAG.
"""
import json
import os
import tempfile
from collections import deque
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st

API = os.environ.get("API_URL", "http://api:8000")
AIRFLOW = os.environ.get("AIRFLOW_URL", "http://airflow-api-server:8080")
DAGS = ["dag_ingestao_preparo", "dag_treino", "dag_scoring"]

st.set_page_config(page_title="Antecipa Recife", layout="wide")

FUSO = "America/Recife"


def api(caminho: str, **params):
    """GET na API; None se ela estiver fora ou responder erro (a aba mostra o aviso)."""
    try:
        r = requests.get(f"{API}{caminho}", params=params, timeout=15)
        return r.json() if r.ok else None
    except requests.RequestException:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def _nomes_locais() -> dict:
    ranking = api("/locais", limit=2000)  # 2000 é o máximo da API e cobre todos os locais
    if not ranking:
        raise RuntimeError("API sem ranking")  # exceção não entra no cache: tenta de novo no próximo ciclo
    return {r["local_id"]: f"{r['bairro']} · {r['logradouro']}" for r in ranking}


def nomes_locais() -> dict:
    """local_id -> "bairro · logradouro", do ranking da API (a telemetria só traz o hash)."""
    try:
        return _nomes_locais()
    except RuntimeError:
        return {}


def data_hora(iso: str | None) -> str:
    """Timestamp ISO (UTC quando vem sem fuso) como 24/11/2026 15:52, no horário do Recife."""
    if not iso:
        return "—"
    t = pd.Timestamp(iso)
    return (t.tz_localize("UTC") if t.tzinfo is None else t).tz_convert(FUSO).strftime("%d/%m/%Y %H:%M")


@st.cache_resource
def ouvinte_mqtt() -> dict:
    """Um assinante por processo do Streamlit; guarda as últimas mensagens em memória."""
    from src.comum import mqtt

    dados = {"telemetria": deque(maxlen=5000), "status": {}, "modelo": None}

    def ao_conectar(cl, *_):
        cl.subscribe([("viario/telemetria", 0), ("viario/status/#", 1), ("viario/modelo/versao", 1)])
        mqtt.publicar_status(cl, "dashboard")

    def ao_receber(cl, userdata, msg):
        try:
            corpo = json.loads(msg.payload)
        except ValueError:
            return
        if msg.topic == "viario/telemetria":
            dados["telemetria"].append(corpo)
        elif msg.topic.startswith("viario/status/"):
            dados["status"][msg.topic.rsplit("/", 1)[-1]] = corpo
        else:
            dados["modelo"] = corpo

    c = mqtt.cliente("dashboard")
    c.on_connect, c.on_message = ao_conectar, ao_receber
    c.connect_async(mqtt.HOST, mqtt.PORTA)
    c.loop_start()
    return dados


@st.cache_data(ttl=30, show_spinner=False)
def ultimas_execucoes() -> pd.DataFrame:
    """Última execução de cada DAG pela API do Airflow 3 (token do simple auth manager)."""
    try:
        token = requests.post(f"{AIRFLOW}/auth/token", timeout=5, json={
            "username": os.environ["AIRFLOW_ADMIN_USER"], "password": os.environ["AIRFLOW_ADMIN_PASSWORD"]}).json()["access_token"]
        linhas = []
        for dag in DAGS:
            r = requests.get(f"{AIRFLOW}/api/v2/dags/{dag}/dagRuns", params={"order_by": "-start_date", "limit": 1},
                             headers={"Authorization": f"Bearer {token}"}, timeout=5).json()
            run = (r.get("dag_runs") or [{}])[0]
            linhas.append({"DAG": dag, "estado": run.get("state", "nunca rodou"), "início": run.get("start_date"),
                           "fim": run.get("end_date")})
        return pd.DataFrame(linhas)
    except (requests.RequestException, KeyError, ValueError) as erro:
        return pd.DataFrame([{"DAG": "—", "estado": f"Airflow indisponível ({type(erro).__name__})"}])


@st.cache_data(ttl=3600, show_spinner=False)
def artefato(run_id: str, caminho: str) -> str:
    """Caminho local de um artefato do run; baixa uma vez, numa pasta fixa por run (o run não muda)."""
    import mlflow

    destino = Path(tempfile.gettempdir()) / "artefatos_mlflow" / run_id
    destino.mkdir(parents=True, exist_ok=True)
    return mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path=caminho, dst_path=str(destino))


dados_mqtt = ouvinte_mqtt()
st.title("Antecipa Recife")
st.subheader("Risco viário no Recife")
st.caption("Locais com maior risco de acidente com vítima no próximo trimestre. Dados: CTTU / Portal de Dados Abertos do Recife.")
abas = st.tabs(["Visão geral", "Locais prioritários", "Métricas do modelo", "Telemetria", "Saúde da solução"])

# ---------- 1. Visão geral ----------
with abas[0]:
    ranking = api("/locais", limit=2000)
    indicadores = api("/indicadores")
    if ranking is None or indicadores is None:
        st.warning("A API ainda não tem scores ou indicadores: rode as DAGs de ingestão, treino e scoring.")
    else:
        ind = pd.DataFrame(indicadores).set_index("ano")
        ind.index = ind.index.astype(str)  # ano como texto: o eixo mostrava "2,015"
        aviso = dados_mqtt["modelo"] or {}
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Acidentes 2015–2024", f"{ind['acidentes'].sum():,}".replace(",", "."))
        c2.metric("Locais monitorados", len(ranking))
        c3.metric("Em risco alto", sum(r["risco_alto"] for r in ranking))
        c4.metric("Última atualização dos scores", data_hora(aviso.get("gerado_em")))
        st.caption(f"Previsão para {ranking[0]['trimestre_alvo']}, a partir dos dados até {ranking[0]['trimestre_base']}.")
        st.subheader("Indicadores do Projeto 6 (atropelamento e usuários vulneráveis)")
        g1, g2 = st.columns(2)
        g1.markdown("**Atropelamentos com vítima e vítimas fatais por ano**")
        barras = (ind[["atropelamentos_com_vitima", "vitimas_fatais"]]
                  .rename(columns={"atropelamentos_com_vitima": "Atropelamentos com vítima", "vitimas_fatais": "Vítimas fatais"})
                  .reset_index().melt("ano", var_name="série", value_name="valor"))
        # Altair em vez de st.bar_chart: a legenda do st.bar_chart corta "Atropelamentos com vítima"
        g1.altair_chart(alt.Chart(barras).mark_bar().encode(
            x=alt.X("ano:N", title=None),
            y=alt.Y("valor:Q", title=None, stack=True),
            color=alt.Color("série:N", title=None, scale=alt.Scale(range=["#0068c9", "#83c9ff"]),
                            legend=alt.Legend(orient="bottom", labelLimit=0)),
            tooltip=["ano", "série", "valor"]), use_container_width=True)
        g2.markdown("**Acidentes com usuário vulnerável envolvido (% dos acidentes do ano)**")
        g2.line_chart(ind[["com_pedestre", "com_ciclista", "com_moto"]].div(ind["acidentes"], axis=0).mul(100).round(1)
                      .rename(columns={"com_pedestre": "Pedestre", "com_ciclista": "Ciclista", "com_moto": "Moto"}))
        st.caption("Contagens de chamados da CTTU, que podem divergir dos relatórios oficiais; 2015 só tem dados a partir de junho; "
                   "a queda de volume a partir de 2020 é do registro, não necessariamente dos sinistros.")

# ---------- 2. Locais prioritários ----------
with abas[1]:
    ranking = api("/locais", limit=2000)
    if ranking is None:
        st.warning("Sem ranking: rode a dag_scoring.")
    else:
        tabela = pd.DataFrame(ranking)
        bairro = st.selectbox("Bairro", ["(todos)"] + sorted(tabela["bairro"].dropna().unique()))
        if bairro != "(todos)":
            tabela = tabela[tabela["bairro"] == bairro]
        st.dataframe(tabela[["posicao", "bairro", "logradouro", "score_vitima", "score_atropelamento", "risco_alto"]],
                     hide_index=True, use_container_width=True)
        escolhido = st.selectbox("Detalhe do local", tabela["local_id"],
                                 format_func=lambda i: " · ".join(map(str, tabela.loc[tabela["local_id"] == i, ["bairro", "logradouro"]].iloc[0])))
        detalhe = api(f"/locais/{escolhido}") if escolhido else None
        if detalhe:
            d1, d2 = st.columns([2, 1])
            d1.markdown(f"**{detalhe['logradouro']} — {detalhe['bairro']}** ({detalhe['n_acidentes_serie']} acidentes na série)")
            d1.line_chart(pd.DataFrame(detalhe["historico"]).set_index("trimestre"))
            d2.markdown("**Features principais (último trimestre)**")
            d2.dataframe(pd.Series(detalhe["features_principais"], name="valor"), use_container_width=True)

# ---------- 3. Métricas do modelo ----------
with abas[2]:
    metricas = api("/metrics")
    if metricas is None:
        st.warning("Sem modelo em produção: rode a dag_treino.")
    else:
        for m in metricas:
            v = m["metricas"]
            st.subheader(f"{m['alvo']} — {m['nome']} v{m['versao']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("PR-AUC (teste 2024)", f"{v.get('test_pr_auc', float('nan')):.3f}",
                      help=f"prevalência {v.get('test_prevalencia', float('nan')):.3f} = PR-AUC de um ranking aleatório")
            c2.metric("Recall@50", f"{v.get('test_recall_at_50', float('nan')):.3f}")
            c3.metric("Recall@100", f"{v.get('test_recall_at_100', float('nan')):.3f}")
            c4.metric("ROC-AUC", f"{v.get('test_roc_auc', float('nan')):.3f}")
            imagens = st.columns(4)
            for coluna, arquivo in zip(imagens, ["matriz_confusao.png", "curva_precisao_recall.png", "curva_roc.png",
                                                 "comparacao_modelos.png"]):
                try:
                    coluna.image(artefato(m["run_id"], arquivo))
                except Exception:
                    coluna.caption(f"{arquivo} indisponível")
            try:
                comparacao = pd.read_csv(artefato(m["run_id"], "comparacao_modelos.csv"), index_col=0)
                st.dataframe(comparacao[["pr_auc", "recall_at_50", "recall_at_100", "roc_auc", "cv_temporal_pr_auc_mean",
                                         "cv_estratificado_pr_auc_mean"]].astype(float).round(3), use_container_width=True)
                st.caption("Validação 2023. cv_estratificado > cv_temporal mostra o vazamento temporal do k-fold no painel.")
            except Exception:
                st.caption("Comparação entre modelos indisponível.")

# ---------- 4. Telemetria ----------
with abas[3]:
    @st.fragment(run_every="5s")
    def telemetria():
        passagens = pd.DataFrame(list(dados_mqtt["telemetria"]))
        if passagens.empty:
            st.info("Nenhuma passagem recebida ainda em viario/telemetria (o simulador publica a cada poucos segundos).")
            return
        nomes = nomes_locais()
        passagens["Local"] = passagens["local_id"].map(nomes).fillna(passagens["local_id"])
        por_local = (passagens.groupby(["Local", "local_id"], as_index=False)
                     .agg(**{"Velocidade média (km/h)": ("velocidade_kmh", "mean"), "Passagens": ("velocidade_kmh", "size"),
                             "Frenagens bruscas": ("frenagem_brusca", "sum")}).round(1))
        por_local = por_local[[c for c in por_local.columns if c != "local_id"] + ["local_id"]]
        st.metric("Passagens recebidas nesta sessão", len(passagens))
        # Altair: o st.bar_chart corta os nomes longos (bairro · logradouro) no eixo
        st.altair_chart(alt.Chart(por_local).mark_bar(color="#0068c9").encode(
            x=alt.X("Velocidade média (km/h):Q"),
            y=alt.Y("Local:N", title=None, sort="-x", axis=alt.Axis(labelLimit=600)),
            tooltip=["Local", "Velocidade média (km/h)", "Passagens", "Frenagens bruscas"]), use_container_width=True)
        st.dataframe(por_local, hide_index=True, use_container_width=True)
        recentes = passagens.tail(10).iloc[::-1].rename(columns={
            "device_id": "Dispositivo", "timestamp": "Horário", "velocidade_kmh": "Velocidade (km/h)",
            "frenagem_brusca": "Frenagem brusca"})
        recentes["Horário"] = recentes["Horário"].map(lambda t: pd.Timestamp(t).tz_convert(FUSO).strftime("%d/%m/%Y %H:%M:%S")
                                                      if pd.Timestamp(t).tzinfo else t)
        st.dataframe(recentes[[c for c in recentes.columns if c != "local_id"] + ["local_id"]], hide_index=True,
                     use_container_width=True)

    telemetria()

# ---------- 5. Saúde da solução ----------
with abas[4]:
    saude = api("/health")
    st.subheader("API, banco e MLflow")
    st.json(saude or {"api": "fora"})
    st.subheader("Serviços (viario/status/#)")
    st.dataframe(pd.DataFrame(dados_mqtt["status"].values()) if dados_mqtt["status"] else pd.DataFrame({"servico": ["nenhum status recebido"]}),
                 hide_index=True, use_container_width=True)
    st.subheader("Última execução de cada DAG")
    st.dataframe(ultimas_execucoes(), hide_index=True, use_container_width=True)
    st.subheader("Modelo em uso")
    st.dataframe(pd.DataFrame(api("/modelo") or []), hide_index=True, use_container_width=True)
