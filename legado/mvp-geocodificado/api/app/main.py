"""API mínima do MVP (semana 0).

Por enquanto só entrega o arquivo de exemplo de trechos (data/contrato/), para a
trilha Embarcados testar o download pelo ESP32 desde já. Na semana 3 (tarefa M5) o
conteúdo passa a vir do modelo de risco, mas o formato da resposta continua o mesmo
(ver docs/09-contrato-trechos-e-telemetria.md).

Rodar a partir da raiz do repositório:
    pip install -r api/requirements.txt
    uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8000
"""
import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
ARQUIVO_TRECHOS = ROOT / "data" / "contrato" / "trechos_exemplo.json"

sys.path.insert(0, str(ROOT / "scripts"))
from validar_trechos import validar  # noqa: E402

app = FastAPI(title="Segurança Viária Recife · Grupo 3", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def carregar() -> dict:
    with open(ARQUIVO_TRECHOS, encoding="utf-8") as f:
        dados = json.load(f)
    erros, _ = validar(dados)
    if erros:
        raise HTTPException(status_code=500, detail={"arquivo_invalido": erros})
    return dados


@app.get("/saude")
def saude():
    return {"ok": True}


@app.get("/trechos")
def trechos(hora: int | None = Query(None, ge=0, le=23, description="Filtra trechos de risco nesse horário")):
    """Lista completa para o painel. Com ?hora=18 devolve só os trechos ativos às 18h."""
    dados = carregar()
    lista = dados["trechos"]
    if hora is not None:
        lista = [t for t in lista if not t["horas"] or hora in t["horas"]]
    return {**dados, "trechos": lista}


@app.get("/modulo/trechos")
def modulo_trechos():
    """Versão para o ESP32: mesmo contrato, sem o campo 'nome' para economizar memória."""
    dados = carregar()
    return {
        "versao": dados["versao"],
        "gerado_em": dados["gerado_em"],
        "trechos": [{k: v for k, v in t.items() if k != "nome"} for t in dados["trechos"]],
    }
