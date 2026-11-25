"""Figura de arquitetura do relatório: reports/figuras/sistema/arquitetura.png (1600x1000 px).

Desenha os containers do docker-compose.yml agrupados por papel e os dois fluxos da solução:
o de dados e modelo (portal -> ingestão -> features -> treino -> MLflow -> scoring -> scores ->
API -> dashboard) e o da telemetria (simulador -> MQTT -> ingestor -> Postgres -> dashboard).

    docker compose run --rm --no-deps tooling python reports/figuras/sistema/arquitetura.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

SAIDA = Path(__file__).with_name("arquitetura.png")

# Uma cor por grupo (fundo claro do grupo, borda e fundo das caixas).
GRUPOS = {
    "MLOps": ("#eef2fb", "#3d5a99"),
    "Dados": ("#eaf5ee", "#2f7a4a"),
    "Aplicação": ("#fdf1e6", "#b3611b"),
    "Mensageria": ("#f6ecf7", "#8a3f91"),
    "Embarcado": ("#f2f2f2", "#555555"),
}
COR_DADOS = "#222222"   # setas do fluxo de dados e modelo
COR_MQTT = "#8a3f91"    # setas de mensagens MQTT

fig = plt.figure(figsize=(16, 10), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 160)
ax.set_ylim(0, 100)
ax.axis("off")
fig.patch.set_facecolor("white")


def grupo(x0, y0, x1, y1, nome, rotulo=None, tracejado=False):
    fundo, borda = GRUPOS[nome] if nome in GRUPOS else ("none", "#999999")
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=1.5",
                                facecolor=fundo, edgecolor=borda, linewidth=1.6,
                                linestyle="--" if tracejado else "-", zorder=1))
    ax.text(x0 + 1.2, y1 - 1.0, rotulo or nome, ha="left", va="top", fontsize=15, fontweight="bold", color=borda, zorder=2)


def caixa(x0, y0, x1, y1, titulo, sub=None, grupo_cor="MLOps", fundo="white"):
    borda = GRUPOS[grupo_cor][1]
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=1",
                                facecolor=fundo, edgecolor=borda, linewidth=2, zorder=3))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if sub:
        ax.text(cx, cy + 1.6, titulo, ha="center", va="center", fontsize=15, fontweight="bold", color="#111111", zorder=4)
        ax.text(cx, cy - 2.2, sub, ha="center", va="center", fontsize=11.5, color="#333333", zorder=4, linespacing=1.3)
    else:
        ax.text(cx, cy, titulo, ha="center", va="center", fontsize=15, fontweight="bold", color="#111111", zorder=4)


def seta(xy0, xy1, texto=None, mqtt=False, curva=0.0, pos=0.5, desloc=(0, 0)):
    cor = COR_MQTT if mqtt else COR_DADOS
    a = FancyArrowPatch(xy0, xy1, arrowstyle="-|>", mutation_scale=20, linewidth=2.2, color=cor,
                        linestyle=(0, (5, 3)) if mqtt else "-", connectionstyle=f"arc3,rad={curva}", zorder=5,
                        shrinkA=2, shrinkB=2)
    # contorno branco: onde duas setas se cruzam, a de cima "passa por cima" da outra
    a.set_path_effects([pe.Stroke(linewidth=6, foreground="white"), pe.Normal()])
    ax.add_patch(a)
    if texto:
        x = xy0[0] + (xy1[0] - xy0[0]) * pos + desloc[0]
        y = xy0[1] + (xy1[1] - xy0[1]) * pos + desloc[1]
        ax.text(x, y, texto, ha="center", va="center", fontsize=11.5, color=cor, zorder=6,
                fontstyle="italic" if mqtt else "normal",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none", alpha=0.95))


ax.text(80, 96.5, "Antecipa Recife: arquitetura", ha="center", va="center", fontsize=26, fontweight="bold", color="#111111")

# ---------- moldura do docker compose e grupos ----------
ax.add_patch(FancyBboxPatch((23, 0.8), 136, 91.2, boxstyle="round,pad=0,rounding_size=2", facecolor="none",
                            edgecolor="#9a9a9a", linewidth=1.4, linestyle=(0, (2, 2)), zorder=0))
ax.text(157.5, 1.6, "docker compose", ha="right", va="bottom", fontsize=12, color="#777777", fontstyle="italic")

grupo(25, 52, 113, 90.5, "MLOps")
grupo(25, 24, 81, 47, "Dados")
grupo(118, 24, 157, 90.5, "Aplicação")
grupo(86, 4, 113, 21, "Mensageria")
grupo(25, 4, 81, 21, "Embarcado")

# ---------- caixas ----------
caixa(1.5, 55, 21, 69, "Portal de Dados", "Abertos do Recife\n(CKAN)", grupo_cor="Embarcado", fundo="#f7f7f7")

ax.add_patch(FancyBboxPatch((27, 53.5), 84, 22.5, boxstyle="round,pad=0,rounding_size=1", facecolor="none",
                            edgecolor="#3d5a99", linewidth=1.2, linestyle=(0, (4, 2)), zorder=2))
ax.text(28.2, 75.2, "Airflow 3", ha="left", va="top", fontsize=13, fontweight="bold", color="#3d5a99", zorder=2)
ax.text(28.2, 72.4, "api-server · scheduler · dag-processor", ha="left", va="top", fontsize=11, color="#3d5a99", zorder=2)
caixa(28.5, 55, 52, 67, "dag_ingestao", "_preparo (mensal)")
caixa(57, 55, 80.5, 67, "dag_treino", "asset features")
caixa(86, 55, 109.5, 67, "dag_scoring", "semanal + asset\nmodelo_campeao")
caixa(57, 78.5, 109.5, 88.5, "mlflow", "Tracking + Model Registry · risco-viario@champion")

ax.text(53, 25.6, "postgres (banco viario)", ha="center", va="center", fontsize=12.5, color="#2f7a4a",
        fontweight="bold", zorder=2)
caixa(27, 28, 43.5, 40, "telemetria", grupo_cor="Dados")
caixa(45.5, 28, 62, 40, "features", "dim_local", grupo_cor="Dados")
caixa(64, 28, 79.5, 40, "scores", grupo_cor="Dados")

caixa(121, 54, 154, 67, "api", "FastAPI · /docs", grupo_cor="Aplicação")
caixa(121, 28, 154, 41, "dashboard", "Streamlit · 5 abas", grupo_cor="Aplicação")

caixa(88, 7, 111, 16.5, "mosquitto", "broker MQTT", grupo_cor="Mensageria")
caixa(40, 7, 58, 16.5, "ingestor", "assina telemetria", grupo_cor="Embarcado")
caixa(62, 7, 79.5, 16.5, "simulador", "ou ESP32", grupo_cor="Embarcado")

# ---------- fluxo de dados e modelo ----------
seta((21, 62), (28.5, 61), "CSVs", pos=0.5, desloc=(0, 2.4))
seta((47, 55), (52.5, 40), "grava", pos=0.3, desloc=(-4.2, 0))
seta((57.5, 40), (64, 55), "lê", pos=0.7, desloc=(2.2, 0))
seta((70, 67), (75, 78.5), "registra", pos=0.5, desloc=(-5.0, 0))
seta((95, 78.5), (98, 67), "carrega\n@champion", pos=0.5, desloc=(6.2, 0))
seta((89, 55), (76, 40), "grava", pos=0.3, desloc=(-3.6, 0))
seta((79.5, 34), (121, 57), "lê scores", pos=0.7, desloc=(2.5, -3.4))
seta((137.5, 54), (137.5, 41), "REST", pos=0.5, desloc=(3.6, 0))
seta((49, 16.5), (38, 28), "grava", pos=0.5, desloc=(3.6, 1.0))

# ---------- MQTT ----------
seta((104, 55), (104, 16.5), "viario/modelo/versao", mqtt=True, pos=0.62)
seta((79.5, 11.5), (88, 11.5), None, mqtt=True)
seta((93, 7), (52, 7), None, mqtt=True, curva=-0.15)
ax.text(72, 3.4, "viario/telemetria: o simulador publica, o ingestor assina", ha="center", va="center", fontsize=11.5,
        color=COR_MQTT, fontstyle="italic", zorder=6,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none"))
seta((111, 12), (128, 28), "telemetria e status (MQTT)", mqtt=True, pos=0.5, desloc=(10.5, -1.0))

fig.savefig(SAIDA, dpi=100, facecolor="white")
print(SAIDA)
