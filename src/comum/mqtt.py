"""Cliente MQTT comum aos serviços (ARCHITECTURE.md, seção 8): login do .env, reconexão
automática e status em viario/status/<servico>."""
import json
import os
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

HOST, PORTA = os.environ.get("MQTT_HOST", "mosquitto"), 1883  # porta dentro da rede do compose


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _status(servico: str, status: str) -> str:
    return json.dumps({"servico": servico, "status": status, "timestamp": agora()})


def cliente(servico: str) -> mqtt.Client:
    """Cliente com login e reconexão; quem chama decide como conectar (connect, connect_async)."""
    c = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"{servico}-{os.getpid()}")
    c.username_pw_set(os.environ["MQTT_USER"], os.environ["MQTT_PASSWORD"])
    c.reconnect_delay_set(min_delay=1, max_delay=30)
    # Se o processo cair sem se despedir, o broker publica "offline" no status dele.
    c.will_set(f"viario/status/{servico}", _status(servico, "offline"), qos=1, retain=True)
    return c


def publicar_status(c: mqtt.Client, servico: str, status: str = "online") -> None:
    c.publish(f"viario/status/{servico}", _status(servico, status), qos=1, retain=True)
