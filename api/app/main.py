"""API do MVP: trechos de risco (M5) e painel com mapa (M6).

Serve data/contrato/trechos.json, gerado pelo modelo de risco (scripts/load_postgis.sh,
configuração escolhida em docs/11). Se esse arquivo não existir, cai para
trechos_exemplo.json e marca as respostas com "aviso": "dados de exemplo".
O formato segue docs/09-contrato-trechos-e-telemetria.md.

Ressalvas (docs/06, docs/11): os trechos vêm de chamados da CTTU, não dos números oficiais
do PSVR; as coordenadas são aproximadas (centro de trecho de rua); o score mede recorrência
histórica, não risco oficial.

Rodar a partir da raiz do repositório:
    pip install -r api/requirements.txt
    uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8000
Painel: http://localhost:8000/painel/
"""
import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
ARQUIVO_TRECHOS = ROOT / "data" / "contrato" / "trechos.json"
ARQUIVO_EXEMPLO = ROOT / "data" / "contrato" / "trechos_exemplo.json"
AVISO_EXEMPLO = "dados de exemplo"

sys.path.insert(0, str(ROOT / "scripts"))
from validar_trechos import validar  # noqa: E402

app = FastAPI(title="Segurança Viária Recife · Grupo 3", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def carregar() -> tuple[dict, str | None]:
    """Devolve (dados do contrato, aviso). aviso = AVISO_EXEMPLO quando caiu no exemplo."""
    caminho, aviso = (ARQUIVO_TRECHOS, None) if ARQUIVO_TRECHOS.exists() else (ARQUIVO_EXEMPLO, AVISO_EXEMPLO)
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    erros, _ = validar(dados)
    if erros:
        raise HTTPException(status_code=500, detail={"arquivo_invalido": caminho.name, "erros": erros})
    return dados, aviso


def com_aviso(resposta: dict, aviso: str | None) -> dict:
    return {**resposta, "aviso": aviso} if aviso else resposta


@app.get("/saude")
def saude():
    dados, aviso = carregar()
    return com_aviso({"ok": True, "fonte": dados["fonte"], "gerado_em": dados["gerado_em"],
                      "total_trechos": len(dados["trechos"])}, aviso)


@app.get("/trechos")
def trechos(hora: int | None = Query(None, ge=0, le=23, description="Filtra trechos de risco nesse horário")):
    """Lista completa para o painel. Com ?hora=18 devolve só os trechos ativos às 18h."""
    dados, aviso = carregar()
    lista = dados["trechos"]
    if hora is not None:
        lista = [t for t in lista if not t["horas"] or hora in t["horas"]]
    return com_aviso({**dados, "trechos": lista}, aviso)


@app.get("/trechos/{trecho_id}")
def trecho(trecho_id: str):
    """Um trecho pelo id (ex.: c1)."""
    dados, aviso = carregar()
    for t in dados["trechos"]:
        if t["id"] == trecho_id:
            return com_aviso(t, aviso)
    raise HTTPException(status_code=404,
                        detail=f"Trecho '{trecho_id}' não existe na fonte '{dados['fonte']}'. "
                               "Veja os ids disponíveis em GET /trechos.")


@app.get("/modulo/trechos")
def modulo_trechos():
    """Versão para o ESP32: mesmo contrato, sem o campo 'nome' para economizar memória.
    Sem 'aviso' de propósito: o formato do módulo é fixo (docs/09); o /saude informa a fonte."""
    dados, _ = carregar()
    return {
        "versao": dados["versao"],
        "gerado_em": dados["gerado_em"],
        "trechos": [{k: v for k, v in t.items() if k != "nome"} for t in dados["trechos"]],
    }
