"""Tests for the embedded side: the route table matches dim_local keys, the simulator payload
follows section 8.2, and the ingestor rejects bad payloads."""
import json
import random
from pathlib import Path

import pandas as pd
import pytest

from embedded.simulador.simulador import passagem
from src.ingestao.telemetria import validar
from src.preparo.local_id import gerar_local_id, normalizar_logradouro, normalizar_texto

ROTA = json.loads((Path(__file__).resolve().parents[1] / "embedded" / "simulador" / "rota.json").read_text(encoding="utf-8"))


def test_rota_usa_o_local_id_de_dim_local():
    pontos = pd.DataFrame(ROTA["pontos"])
    esperado = gerar_local_id(normalizar_texto(pontos["bairro"]), normalizar_logradouro(pontos["logradouro"]))
    assert pontos["local_id"].tolist() == esperado.tolist()


def test_payload_do_simulador_passa_no_ingestor():
    p = passagem(ROTA["pontos"][0], random.Random(0))
    assert set(p) == {"device_id", "local_id", "lat", "lon", "timestamp", "velocidade_kmh", "frenagem_brusca"}
    assert validar(json.dumps(p).encode())["local_id"] == ROTA["pontos"][0]["local_id"]


@pytest.mark.parametrize("estrago", [{"local_id": "nao-e-hash"}, {"local_id": "7c0fbb1fe74c\n"},
                                     {"frenagem_brusca": "sim"}, {"velocidade_kmh": -5},
                                     {"timestamp": "2026-11-18T10:00:00"}, {"lat": 200}])
def test_ingestor_recusa_payload_ruim(estrago):
    p = {**passagem(ROTA["pontos"][0], random.Random(0)), **estrago}
    with pytest.raises(ValueError):
        validar(json.dumps(p).encode())


def test_ingestor_recusa_json_quebrado():
    with pytest.raises(ValueError):
        validar(b"{nao e json")
