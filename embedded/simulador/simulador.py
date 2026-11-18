"""Simulador do sistema embarcado (ARCHITECTURE.md, seção 8.1).

Percorre a rota embarcada (rota.json, derivada de dim_local) e publica uma passagem de veículo
por vez em viario/telemetria, com o payload da seção 8.2: lat/lon simulados e o local_id que a
tabela de rota associa ao ponto. Velocidade sorteada em torno do limite da via; frenagem brusca
em 5% das passagens. Publica online/offline em viario/status/simulador.
"""
import itertools
import json
import os
import random
import time
from pathlib import Path

from src.comum import mqtt

ROTA = Path(__file__).with_name("rota.json")
INTERVALO_S = float(os.environ.get("SIMULADOR_INTERVALO_S", 2))
DEVICE_ID = "simulador-01"


def passagem(ponto: dict, rng: random.Random) -> dict:
    limite = ponto["velocidade_max_kmh"]
    return {
        "device_id": DEVICE_ID,
        "local_id": ponto["local_id"],
        # Ruído de ~30 m em volta do ponto, como um GPS faria.
        "lat": round(ponto["lat"] + rng.uniform(-3e-4, 3e-4), 6),
        "lon": round(ponto["lon"] + rng.uniform(-3e-4, 3e-4), 6),
        "timestamp": mqtt.agora(),
        "velocidade_kmh": round(max(0.0, rng.gauss(0.9 * limite, 0.2 * limite)), 1),
        "frenagem_brusca": rng.random() < 0.05,
    }


def main() -> None:
    pontos = json.loads(ROTA.read_text(encoding="utf-8"))["pontos"]
    rng = random.Random(42)
    c = mqtt.cliente("simulador")
    c.on_connect = lambda cl, *_: mqtt.publicar_status(cl, "simulador")  # também a cada reconexão
    c.connect_async(mqtt.HOST, mqtt.PORTA)
    c.loop_start()  # reconecta sozinho; publish enfileira enquanto o broker estiver fora
    for i in itertools.count():
        c.publish("viario/telemetria", json.dumps(passagem(pontos[i % len(pontos)], rng)), qos=1)
        time.sleep(INTERVALO_S)


if __name__ == "__main__":
    main()
