"""Testes da API do MVP (api/app/main.py). Sem internet e sem Docker: usam um trechos.json
pequeno em tmp_path, via monkeypatch no caminho do arquivo."""
import json

import pytest
from fastapi.testclient import TestClient

from api.app import main

CONTRATO = {
    "versao": 1,
    "gerado_em": "2026-11-06T09:00:00-03:00",
    "fonte": "teste",
    "trechos": [
        {"id": "c1", "nome": "AV CAXANGA", "lat": -8.0308, "lon": -34.95664, "raio_m": 200,
         "risco": "alto", "score": 1.0, "horas": [6, 7, 8], "vel_segura": 30},
        {"id": "c2", "nome": "AV RECIFE", "lat": -8.1, "lon": -34.92, "raio_m": 250,
         "risco": "medio", "score": 0.5, "horas": [], "vel_segura": 50},
        {"id": "c3", "nome": "AV NORTE", "lat": -8.03, "lon": -34.89, "raio_m": 200,
         "risco": "baixo", "score": 0.2, "horas": [18, 19], "vel_segura": 30},
    ],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    arquivo = tmp_path / "trechos.json"
    arquivo.write_text(json.dumps(CONTRATO), encoding="utf-8")
    monkeypatch.setattr(main, "ARQUIVO_TRECHOS", arquivo)
    return TestClient(main.app)


def test_saude(client):
    r = client.get("/saude")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "fonte": "teste", "gerado_em": "2026-11-06T09:00:00-03:00",
                        "total_trechos": 3}


def test_trechos_lista_completa(client):
    r = client.get("/trechos")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo == CONTRATO  # mesmo formato do contrato, sem "aviso"


def test_trechos_filtro_por_hora(client):
    # horas vazia = vale o dia todo, então c2 aparece em qualquer hora
    assert [t["id"] for t in client.get("/trechos?hora=7").json()["trechos"]] == ["c1", "c2"]
    assert [t["id"] for t in client.get("/trechos?hora=18").json()["trechos"]] == ["c2", "c3"]
    assert [t["id"] for t in client.get("/trechos?hora=3").json()["trechos"]] == ["c2"]


@pytest.mark.parametrize("hora", [-1, 24, "x"])
def test_trechos_hora_invalida(client, hora):
    assert client.get(f"/trechos?hora={hora}").status_code == 422


def test_trecho_por_id(client):
    r = client.get("/trechos/c3")
    assert r.status_code == 200
    assert r.json() == CONTRATO["trechos"][2]


def test_trecho_inexistente_404(client):
    r = client.get("/trechos/nao-existe")
    assert r.status_code == 404
    assert "nao-existe" in r.json()["detail"]
    assert "GET /trechos" in r.json()["detail"]


def test_modulo_trechos_sem_nome(client):
    r = client.get("/modulo/trechos")
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == {"versao", "gerado_em", "trechos"}
    assert len(corpo["trechos"]) == 3
    assert all("nome" not in t for t in corpo["trechos"])
    assert corpo["trechos"][0] == {k: v for k, v in CONTRATO["trechos"][0].items() if k != "nome"}


def test_fallback_para_exemplo(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ARQUIVO_TRECHOS", tmp_path / "nao_existe.json")
    client = TestClient(main.app)
    exemplo = json.loads(main.ARQUIVO_EXEMPLO.read_text(encoding="utf-8"))

    saude = client.get("/saude").json()
    assert saude["aviso"] == "dados de exemplo"
    assert saude["fonte"] == exemplo["fonte"]
    assert saude["total_trechos"] == len(exemplo["trechos"])

    trechos = client.get("/trechos").json()
    assert trechos["aviso"] == "dados de exemplo"
    assert trechos["trechos"] == exemplo["trechos"]

    primeiro = exemplo["trechos"][0]["id"]
    assert client.get(f"/trechos/{primeiro}").json()["aviso"] == "dados de exemplo"
    assert "aviso" not in client.get("/modulo/trechos").json()


def test_arquivo_invalido_500(tmp_path, monkeypatch):
    arquivo = tmp_path / "trechos.json"
    arquivo.write_text(json.dumps({**CONTRATO, "versao": 0}), encoding="utf-8")
    monkeypatch.setattr(main, "ARQUIVO_TRECHOS", arquivo)
    r = TestClient(main.app).get("/trechos")
    assert r.status_code == 500
    assert r.json()["detail"]["arquivo_invalido"] == "trechos.json"


def test_arquivo_real_e_valido():
    """O trechos.json versionado (se existir) passa no validador do contrato."""
    if not main.ARQUIVO_TRECHOS.exists():
        pytest.skip("data/contrato/trechos.json não gerado")
    dados, aviso = main.carregar()
    assert aviso is None
    assert dados["trechos"]


def test_painel_servido(client):
    r = client.get("/painel/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "leaflet@1.9.4" in r.text
    assert 'fetch(url)' in r.text and '"/trechos"' in r.text
