"""Ingestor MQTT -> Postgres (ARCHITECTURE.md, seção 8.3).

Assina viario/telemetria e grava cada passagem válida na tabela telemetria. O payload vem da
rede, então cada campo é conferido antes de entrar no banco; mensagem inválida é registrada no
log e descartada. O loop do paho reconecta sozinho se o broker cair, e a assinatura é refeita a
cada reconexão. Publica online/offline em viario/status/ingestor.
"""
import json
import logging
import re
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.comum import mqtt
from src.comum.db import engine

TABELA = """
CREATE TABLE IF NOT EXISTS telemetria (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    local_id TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    momento TIMESTAMPTZ NOT NULL,
    velocidade_kmh DOUBLE PRECISION NOT NULL,
    frenagem_brusca BOOLEAN NOT NULL,
    recebido_em TIMESTAMPTZ NOT NULL DEFAULT now()
)"""
INSERIR = text("INSERT INTO telemetria (device_id, local_id, lat, lon, momento, velocidade_kmh, frenagem_brusca) "
               "VALUES (:device_id, :local_id, :lat, :lon, :momento, :velocidade_kmh, :frenagem_brusca)")
LOCAL_ID = re.compile(r"[0-9a-f]{12}")


def validar(payload: bytes) -> dict:
    """Converte e confere o payload da seção 8.2; levanta ValueError se algo não bater."""
    try:
        d = json.loads(payload)
        p = {"device_id": str(d["device_id"])[:64], "local_id": str(d["local_id"]),
             "lat": float(d["lat"]), "lon": float(d["lon"]),
             "momento": datetime.fromisoformat(str(d["timestamp"]).replace("Z", "+00:00")),
             "velocidade_kmh": float(d["velocidade_kmh"]), "frenagem_brusca": d["frenagem_brusca"]}
    except (KeyError, TypeError, ValueError) as erro:  # JSONDecodeError é ValueError
        raise ValueError(f"payload malformado: {erro}") from erro
    if not LOCAL_ID.fullmatch(p["local_id"]):  # match com $ aceitaria um \n no fim
        raise ValueError("local_id não tem o formato de dim_local (12 hex)")
    if not isinstance(p["frenagem_brusca"], bool):
        raise ValueError("frenagem_brusca não é booleano")
    if not (0 <= p["velocidade_kmh"] <= 300 and -90 <= p["lat"] <= 90 and -180 <= p["lon"] <= 180):
        raise ValueError("velocidade ou coordenada fora da faixa")
    if p["momento"].tzinfo is None:
        raise ValueError("timestamp sem fuso horário")
    return p


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    banco = engine()
    with banco.begin() as con:
        con.execute(text(TABELA))

    def ao_conectar(cl, userdata, flags, reason, props):
        cl.subscribe("viario/telemetria", qos=1)
        mqtt.publicar_status(cl, "ingestor")

    def ao_receber(cl, userdata, msg):
        try:
            passagem = validar(msg.payload)
            with banco.begin() as con:
                con.execute(INSERIR, passagem)
        except ValueError as erro:
            logging.warning("mensagem descartada: %s", erro)
        except SQLAlchemyError as erro:  # banco fora: registra e segue; a reconexão é do pool
            logging.error("falha ao gravar passagem: %s", erro)

    c = mqtt.cliente("ingestor")
    c.on_connect, c.on_message = ao_conectar, ao_receber
    c.connect_async(mqtt.HOST, mqtt.PORTA)
    c.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
