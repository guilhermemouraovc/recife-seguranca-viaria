"""Tests for scripts/geocode_sinistros.py -- no network: requests is mocked everywhere."""
import json
import sys
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import geocode_sinistros as geo  # noqa: E402
from geocode_sinistros import coordenada_final  # noqa: E402

HIT_NUMERO = {"lat": "-8.02", "lon": "-34.91", "display_name": "48, Rua Taquaratinga, Casa Amarela, Recife",
              "osm_type": "node", "osm_id": 1, "category": "place", "type": "house",
              "address": {"house_number": "48", "road": "Rua Taquaratinga", "suburb": "Casa Amarela",
                          "city": "Recife"}}
HIT_VIA = {"lat": "-8.03", "lon": "-34.92", "display_name": "Avenida Beberibe, Ponto de Parada, Recife",
           "osm_type": "way", "osm_id": 2, "category": "highway", "type": "primary",
           "address": {"road": "Avenida Beberibe", "suburb": "Ponto de Parada", "city_district": "Recife"}}


def response(status=200, payload=None):
    r = mock.Mock(status_code=status)
    r.json.return_value = payload if payload is not None else []
    r.text = ""
    r.raise_for_status.side_effect = None if status < 400 else requests.HTTPError(str(status))
    return r


def client(*responses):
    session = mock.Mock(headers={})
    session.get.side_effect = list(responses)
    sleeps = []
    return geo.Nominatim("teste@exemplo.org", session=session, sleep=sleeps.append, clock=lambda: 0.0), session, sleeps


@pytest.mark.parametrize("norm, original, expected", [
    ("AV CAXANGA", "AV CAXANGA", "Avenida CAXANGA"),
    ("R DIADEMA", "RUA DIADEMA", "RUA DIADEMA"),
    ("R DA AURORA", "R. DA AURORA", "Rua DA AURORA"),
    ("EST DE BELEM", "EST DE BELEM", "Estrada DE BELEM"),
    ("PCA DO DERBY", None, "Praça DO DERBY"),
    ("PRC DE CASA FORTE", "PRC DE CASA FORTE", "Praça DE CASA FORTE"),
    ("TV DO RAPOSO", "TV DO RAPOSO", "Travessa DO RAPOSO"),
    ("C SANTA RITA", "C SANTA RITA", "Cais SANTA RITA"),
    ("BR 101 DENTRO DA CEASA", "BR 101 (DENTRO DA CEASA)", "BR 101 DENTRO DA CEASA"),
])
def test_expandir_rua(norm, original, expected):
    assert geo.expandir_rua(norm, original) == expected


def test_tres_tentativas_com_numero():
    tents = geo.tentativas("AV NORTE", "AV NORTE", "1250", "CASA AMARELA")
    assert tents == [
        ("a", {"street": "1250 Avenida NORTE", "city": "Recife", "state": "Pernambuco"}),
        ("b", {"street": "Avenida NORTE", "city": "Recife", "state": "Pernambuco"}),
        ("c", {"q": "Avenida NORTE, CASA AMARELA, Recife, Pernambuco"}),
    ]


@pytest.mark.parametrize("numero", ["XX", "S/N", "312A", "0", "", None])
def test_numero_invalido_pula_tentativa_a(numero):
    assert [t for t, _ in geo.tentativas("AV NORTE", "AV NORTE", numero, "CASA AMARELA")] == ["b", "c"]


def test_parametros_fixos_e_user_agent():
    c, session, _ = client(response(payload=[HIT_VIA]))
    c.search({"street": "Avenida BEBERIBE", "city": "Recife", "state": "Pernambuco"})
    params = session.get.call_args.kwargs["params"]
    assert params["viewbox"] == "-35.10,-7.80,-34.80,-8.30" and params["bounded"] == 1
    assert params["countrycodes"] == "br" and params["format"] == "jsonv2" and params["limit"] == 1
    assert "teste@exemplo.org" in session.headers["User-Agent"]


HIT_VIA_ENCRUZILHADA = {**HIT_VIA, "lat": "-8.04", "lon": "-34.89",
                        "display_name": "Avenida Beberibe, Encruzilhada, Recife",
                        "address": {"road": "Avenida Beberibe", "suburb": "Encruzilhada"}}


def test_cai_para_proxima_tentativa_e_cache_evita_repeticao(tmp_path):
    cache_path = tmp_path / "cache.csv"
    combos = [("AV BEBERIBE", "AV BEBERIBE", "999", "PONTO DE PARADA")]
    c, session, _ = client(response(payload=[]), response(payload=[HIT_VIA]))
    cache = {}
    stats = geo.geocode(combos, cache, c, cache_path=cache_path)
    assert stats["consultas"] == 2  # (a) failed, (b) found in the right bairro, (c) not needed
    tentativas = {row["tentativa"]: row["nivel"] for row in cache.values()}
    assert tentativas == {"a": "falhou", "b": "via"}

    # Re-run from the saved file: everything is resolved, no request at all.
    c2, session2, _ = client()
    stats2 = geo.geocode(combos, geo.load_cache(cache_path), c2, cache_path=cache_path)
    assert stats2 == {"combinacoes": 1, "ja_resolvidas": 1, "processadas": 0, "consultas": 0}
    session2.get.assert_not_called()


def test_bairro_errado_em_b_tambem_consulta_c_e_usa_c_se_conferir(tmp_path):
    combo = ("AV BEBERIBE", "AV BEBERIBE", None, "ENCRUZILHADA")
    c, session, _ = client(response(payload=[HIT_VIA]), response(payload=[HIT_VIA_ENCRUZILHADA]))
    cache = {}
    assert geo.geocode([combo], cache, c, cache_path=tmp_path / "c.csv")["consultas"] == 2
    assert session.get.call_args.kwargs["params"]["q"] == "Avenida BEBERIBE, ENCRUZILHADA, Recife, Pernambuco"
    row = geo.resolver(geo.tentativas(*combo), cache, combo[3])
    assert row["tentativa"] == "c" and row["bairro_ok"] and row["lat"] == "-8.04"


def test_c_que_tambem_nao_confere_mantem_resultado_de_b(tmp_path):
    combo = ("AV BEBERIBE", "AV BEBERIBE", None, "CAJUEIRO")
    c, _, _ = client(response(payload=[HIT_VIA]), response(payload=[HIT_VIA_ENCRUZILHADA]))
    cache = {}
    geo.geocode([combo], cache, c, cache_path=tmp_path / "c.csv")
    row = geo.resolver(geo.tentativas(*combo), cache, combo[3])
    assert row["tentativa"] == "b" and not row["bairro_ok"]
    # Both cached: nothing left to ask.
    assert geo.proxima_consulta(geo.tentativas(*combo), cache, combo[3]) is None


def test_falha_total_fica_no_cache(tmp_path):
    combos = [("R INEXISTENTE", None, None, "PINA")]
    c, session, _ = client(response(payload=[]), response(payload=[]))
    cache = {}
    geo.geocode(combos, cache, c, cache_path=tmp_path / "c.csv")
    assert session.get.call_count == 2
    assert geo.resolver(geo.tentativas(*combos[0]), cache, "PINA")["nivel"] == "falhou"


def test_429_faz_backoff_e_tenta_de_novo():
    c, session, sleeps = client(response(429), response(503), response(payload=[HIT_NUMERO]))
    hit = c.search({"street": "48 Rua TAQUARITINGA", "city": "Recife", "state": "Pernambuco"})
    assert hit is HIT_NUMERO
    assert session.get.call_count == 3
    assert 5 in sleeps and 10 in sleeps  # 5 s, then 10 s


def test_429_desiste_depois_de_3_retries():
    c, session, _ = client(*[response(429)] * 4)
    with pytest.raises(requests.HTTPError):
        c.search({"q": "x"})
    assert session.get.call_count == 4


def test_403_para_tudo():
    c, session, _ = client(response(403), response(payload=[HIT_VIA]))
    with pytest.raises(geo.NominatimForbidden):
        c.search({"q": "x"})
    assert session.get.call_count == 1


def test_intervalo_minimo_entre_requisicoes():
    clock = iter([0.0, 0.3, 1.1])  # 1st call starts at 0.0; 2nd asks at 0.3, starts after the wait
    session = mock.Mock(headers={})
    session.get.side_effect = [response(payload=[]), response(payload=[])]
    sleeps = []
    c = geo.Nominatim("x", session=session, sleep=sleeps.append, clock=lambda: next(clock))
    c.search({"q": "a"})
    c.search({"q": "b"})
    assert sleeps == [pytest.approx(geo.MIN_INTERVAL_S - 0.3)]


def test_parse_hit_niveis():
    assert geo.parse_hit(HIT_NUMERO)["nivel"] == "numero"
    assert geo.parse_hit(HIT_VIA)["nivel"] == "via"
    assert geo.parse_hit({**HIT_VIA, "category": "place", "type": "suburb", "address": {}})["nivel"] == "outro"
    assert geo.parse_hit(None) == {"nivel": "falhou"}


def test_bairro_confere_em_qualquer_nivel_abaixo_da_cidade():
    comp = json.dumps({"suburb": "Ibura de Baixo", "city_district": "Ibura", "city": "Recife"})
    assert geo.bairro_confere("IBURA", comp)
    assert geo.bairro_confere("Ibura de Baixo", comp)
    assert not geo.bairro_confere("RECIFE", comp)
    assert not geo.bairro_confere("PINA", comp)
    # addressdetails keeps one value per level; the official bairro may be only in display_name.
    assert geo.bairro_confere("VÁRZEA", json.dumps({"suburb": "UR-07"}), "Rua Caburaí, UR-07, Várzea, Recife")
    assert not geo.bairro_confere("RECIFE", "{}", "Rua X, Recife, Pernambuco")


def test_rua_confere():
    comp = lambda road: json.dumps({"road": road})  # noqa: E731
    assert geo.rua_confere("48 Rua TAQUARITINGA", comp("Rua Taquaratinga"))
    assert geo.rua_confere("Avenida DR JOSE RUFINO", comp("Avenida Doutor José Rufino"))
    assert not geo.rua_confere("RUA DA CUSTODIA", comp("Rua Rosário de Minas"))


SEM = (-8.05, -34.90)
GEO = lambda nivel, bairro_ok=True, rua_ok=True: {"lat": "-8.10", "lon": "-34.95", "nivel": nivel,  # noqa: E731
                                                  "bairro_ok": bairro_ok, "rua_ok": rua_ok}


@pytest.mark.parametrize("sem, confere, g, fonte", [
    (SEM, True, GEO("numero"), "semaforo"),
    (SEM, False, GEO("numero"), "endereco_numero"),
    (None, None, GEO("via"), "endereco_via"),
    (SEM, False, GEO("via", bairro_ok=False), "semaforo_nao_confere"),
    (SEM, False, None, "semaforo_nao_confere"),
    (None, None, GEO("numero", bairro_ok=False), "endereco_nao_confere"),
    (None, None, GEO("outro"), "endereco_nao_confere"),
    (None, None, GEO("via", rua_ok=False), None),
    (None, None, GEO("falhou"), None),
    (None, None, None, None),
])
def test_prioridade_da_coordenada(sem, confere, g, fonte):
    lat, lon, got = coordenada_final(sem, confere, g)
    assert got == fonte
    if fonte is None:
        assert lat is None and lon is None
    elif fonte.startswith("semaforo"):
        assert (lat, lon) == SEM
    else:
        assert (lat, lon) == (-8.10, -34.95)


@pytest.mark.parametrize("raw, expected", [
    ("Av. Eng. José Estelita,", "AV ENG JOSE ESTELITA"),
    ("AVENIDA  CAXANGÁ", "AV CAXANGA"),
    ("Rua da Aurora", "R DA AURORA"),
    ("R. DA AURORA", "R DA AURORA"),
    ("Estrada do Arraial", "EST DO ARRAIAL"),
    ("Praça do Derby", "PCA DO DERBY"),
    ("Av.Cruz Cabugá", "AV CRUZ CABUGA"),
    ("RUA 15 DE MARÇO", "R 15 DE MARCO"),
    ("", None),
    (None, None),
])
def test_normalize_endereco(raw, expected):
    assert geo.normalize_endereco(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("37", "37"), ("037", "37"), ("009", "9"), ("37,0", "37"), ("510.0", "510"), (" 174 ", "174"),
    (37, "37"), ("0", None), ("0,0", None), ("", None), ("S/N", None), ("37,5", None), (None, None),
])
def test_normalize_num_semaforo(raw, expected):
    assert geo.normalize_num_semaforo(raw) == expected


def test_semaforo_confere_por_bairro_ou_rua():
    tokens = geo.street_tokens("Av. Boa Viagem Rua Thomé Gibson")
    assert geo.semaforo_confere("BOA VIAGEM", "AV CONSELHEIRO AGUIAR", "BOA VIAGEM", tokens)
    assert geo.semaforo_confere("PINA", "RUA THOME GIBSON", "BOA VIAGEM", tokens)
    assert not geo.semaforo_confere("SANTO AMARO", "AV CRUZ CABUGA", "BOA VIAGEM", tokens)


def test_preparar_e_aplicar_offline():
    sem = pd.DataFrame({"semaforo_norm": ["37"], "latitude": [-8.05], "longitude": [-34.90],
                        "sem_bairro": ["BOA VIAGEM"], "sem_tokens": [{"VIAGEM"}]})
    df = pd.DataFrame({"endereco": ["AV BOA VIAGEM", "AV BEBERIBE", "AV CRUZ CABUGA"],
                       "numero": [None, None, None], "bairro": ["BOA VIAGEM", "PONTO DE PARADA", "SANTO AMARO"],
                       "num_semaforo": pd.array([37, pd.NA, 37], dtype="Int64")})
    df = geo.preparar(df, sem)
    assert df["coord_confere"].tolist() == [True, pd.NA, False]
    assert len(geo.pendentes(df)) == 2  # the matching traffic light is never geocoded
    tents = geo.tentativas("AV BEBERIBE", "AV BEBERIBE", None, "PONTO DE PARADA")
    key = geo.chave(tents[0][1])
    cache = {key: {"chave": key, "tentativa": "b", **geo.parse_hit(HIT_VIA)}}
    out, stats = geo.aplicar(df, cache)
    assert out["geo_precisao"].tolist() == ["semaforo", "endereco_via", "semaforo_nao_confere"]
    assert out["coord_precisao"].tolist() == ["alta", "media", "baixa"]
    assert stats["situacao_por_linha"]["pendente"] == 1


def test_importar_cache_json_antigo():
    legacy = {
        "AV BEBERIBE|ENCRUZILHADA": {"lat": -8.04, "lon": -34.89, "display_name": "Avenida Beberibe, Encruzilhada, Recife",
                                     "precisao": "via_bairro"},
        "R INEXISTENTE|PINA": None,
    }
    cache = {}
    assert geo.importar_cache_json(legacy, cache) == 3
    t = geo.tentativas("AV BEBERIBE", "AV BEBERIBE", None, "ENCRUZILHADA")
    c_row = cache[geo.chave(t[1][1])]
    assert c_row["tentativa"] == "c" and c_row["nivel"] == "via"
    # display_name alone is enough for the checks when there is no addressdetails.
    assert geo._confere(geo.avaliar(c_row, t[1][1], "ENCRUZILHADA"))
    falhas = [r for r in cache.values() if r["nivel"] == "falhou"]
    assert {r["tentativa"] for r in falhas} == {"b", "c"}
    # Existing rows are never overwritten.
    assert geo.importar_cache_json(legacy, cache) == 0


def test_cache_versionado_fora_de_processed():
    assert geo.CACHE_PATH.parent.name == "geocode"
    assert "processed" not in geo.CACHE_PATH.parts


def test_main_para_sem_contato(monkeypatch, tmp_path):
    monkeypatch.delenv("NOMINATIM_CONTACT", raising=False)
    monkeypatch.setattr(geo, "IN_PATH", tmp_path / "x.parquet")
    (tmp_path / "x.parquet").write_bytes(b"")
    monkeypatch.setattr(sys, "argv", ["geocode_sinistros.py"])
    assert geo.main() == 2
