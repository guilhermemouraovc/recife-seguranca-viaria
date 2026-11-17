"""Simula o módulo veicular publicando telemetria MQTT no formato do docs/09 (parte 2).

Serve para demonstrar o painel (aba Módulo) sem o ESP32. Percorre uma rota que passa por
trechos reais de data/contrato/trechos.json e decide o alerta com a mesma regra do firmware
(embarcados/simulacao/sketch.ino): fora de trecho = verde; dentro e até a vel. segura =
amarelo; acima = vermelho, com histerese de 3 km/h para sair do vermelho.

Todo dado sai com fonte_vel = "sim" (bancada): não misturar com medição de rua (docs/09).
O broker padrão é público e sem senha: qualquer um vê e pode publicar nesses tópicos.

    .venv/bin/python scripts/simular_modulo.py              # roda até Ctrl+C
    .venv/bin/python scripts/simular_modulo.py --hora 8     # força o horário (testar faixas)
    .venv/bin/python scripts/simular_modulo.py --teste      # só a auto-checagem, sem rede
"""
import argparse
import json
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUSO = timezone(timedelta(hours=-3))
HISTERESE_KMH = 3

# Rota de ida e volta: Derby (Agamenon) -> Conde da Boa Vista -> Cruz Cabugá, começando e
# terminando fora dos trechos. ponytail: rota fixa; trocar os pontos se os trechos mudarem.
ROTA = [(-8.0530, -34.9050), (-8.05509, -34.89762), (-8.05700, -34.89300),
        (-8.05863, -34.88816), (-8.05700, -34.88500), (-8.05541, -34.88242), (-8.05000, -34.87800)]


def distancia_m(lat1, lon1, lat2, lon2):
    r, rad = 6371000, math.pi / 180
    dlat, dlon = (lat2 - lat1) * rad, (lon2 - lon1) * rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def trecho_atual(trechos, lat, lon, hora):
    """Primeiro trecho cujo raio contém o ponto e que está ativo na hora ([] = dia todo)."""
    for t in trechos:
        if distancia_m(lat, lon, t["lat"], t["lon"]) <= t["raio_m"] and (not t["horas"] or hora in t["horas"]):
            return t
    return None


def decidir(trecho, vel, anterior):
    if trecho is None:
        return "verde"
    if vel > trecho["vel_segura"]:
        return "vermelho"
    if anterior == "vermelho" and vel >= trecho["vel_segura"] - HISTERESE_KMH:
        return "vermelho"
    return "amarelo"


def posicao(fase):
    """fase 0..1 -> ponto na rota (ida até 0,5, volta depois), interpolando entre os pontos."""
    f = fase * 2 if fase < 0.5 else (1 - fase) * 2
    x = f * (len(ROTA) - 1)
    i = min(int(x), len(ROTA) - 2)
    k = x - i
    (a_lat, a_lon), (b_lat, b_lon) = ROTA[i], ROTA[i + 1]
    return a_lat + (b_lat - a_lat) * k, a_lon + (b_lon - a_lon) * k


def velocidade(t):
    """20..55 km/h oscilando: cruza a vel. segura de 30 km/h dentro dos trechos."""
    return round(37 + 18 * math.sin(t / 7))


def teste():
    t = {"id": "x", "lat": -8.0, "lon": -34.9, "raio_m": 200, "vel_segura": 30, "horas": [6, 7]}
    assert trecho_atual([t], -8.0, -34.9, 6) is t
    assert trecho_atual([t], -8.0, -34.9, 12) is None          # fora do horário
    assert trecho_atual([t], -8.01, -34.9, 6) is None          # ~1,1 km longe
    assert trecho_atual([{**t, "horas": []}], -8.0, -34.9, 3)  # [] = dia todo
    assert decidir(None, 80, "vermelho") == "verde"
    assert decidir(t, 31, "verde") == "vermelho"
    assert decidir(t, 28, "vermelho") == "vermelho"            # histerese
    assert decidir(t, 26, "vermelho") == "amarelo"
    assert posicao(0) == ROTA[0] and posicao(0.5) == ROTA[-1]
    print("ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", default="broker.hivemq.com")
    ap.add_argument("--porta", type=int, default=1883)
    ap.add_argument("--modulo", default="sim-painel")
    ap.add_argument("--hora", type=int, help="força a hora 0-23 (padrão: hora atual de Recife)")
    ap.add_argument("--periodo", type=int, default=90, help="segundos para ida e volta na rota")
    ap.add_argument("--teste", action="store_true")
    args = ap.parse_args()
    if args.teste:
        return teste()

    import paho.mqtt.client as mqtt

    dados = json.loads((ROOT / "data" / "contrato" / "trechos.json").read_text(encoding="utf-8"))
    base = f"p6g3/modulo/{args.modulo}"
    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{args.modulo}-{int(time.time())}")
    cli.will_set(f"{base}/status", "offline", qos=1, retain=True)
    cli.connect(args.broker, args.porta, keepalive=30)
    cli.loop_start()
    cli.publish(f"{base}/status", "online", qos=1, retain=True)
    print(f"publicando em {args.broker}: {base}/telemetria|alerta|status (Ctrl+C para parar)")

    nivel, inicio = "verde", time.time()
    try:
        while True:
            agora = datetime.now(FUSO)
            t = time.time() - inicio
            lat, lon = posicao((t % args.periodo) / args.periodo)
            vel = velocidade(t)
            hora = agora.hour if args.hora is None else args.hora
            trecho = trecho_atual(dados["trechos"], lat, lon, hora)
            novo = decidir(trecho, vel, nivel)
            msg = {"ts": agora.isoformat(timespec="seconds"), "lat": round(lat, 5), "lon": round(lon, 5),
                   "vel": vel, "fonte_vel": "sim", "trecho": trecho["id"] if trecho else None,
                   "alerta": novo, "versao_trechos": dados["versao"]}
            payload = json.dumps(msg)
            if novo != nivel:
                cli.publish(f"{base}/alerta", payload, qos=1)
            nivel = novo
            cli.publish(f"{base}/telemetria", payload, qos=0)
            print(f"{msg['ts'][11:19]}  {vel:3d} km/h  {msg['trecho'] or '-':4}  {novo}")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cli.publish(f"{base}/status", "offline", qos=1, retain=True).wait_for_publish(3)
        cli.loop_stop()
        cli.disconnect()


if __name__ == "__main__":
    main()
