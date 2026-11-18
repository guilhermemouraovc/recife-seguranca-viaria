# Módulo de telemetria (ESP32)

Trilha Sistemas Embarcados. Contrato e papel do módulo: `ARCHITECTURE.md`, seção 8.

O módulo fica associado a **um local** da solução, identificado pelo `local_id` (texto de
bairro + logradouro normalizado, `ARCHITECTURE.md` seção 3.1). Ele não usa GPS nem
coordenadas e não emite alerta: só mede e publica. O modelo de risco agrega essas passagens
por local × trimestre como features de telemetria (seção 3.3).

O módulo:

1. lê a velocidade (CAN/OBD-II, ou potenciômetro na bancada);
2. marca `frenagem_brusca` quando a velocidade cai rápido demais entre duas leituras;
3. publica cada passagem via MQTT no tópico `viario/telemetria`.

O `embedded/simulador/` (próxima rodada) publica o mesmo payload e é o que roda no
`docker-compose.yml`. O ESP32 é opcional na demonstração.

## Payload

Tópico `viario/telemetria`, JSON, uma mensagem por passagem:

```json
{
  "device_id": "bancada-01",
  "local_id": "3f2a9c1b7e04",
  "timestamp": "2026-11-16T14:03:22Z",
  "velocidade_kmh": 47.5,
  "frenagem_brusca": false
}
```

| Campo | Tipo | Origem |
|---|---|---|
| `device_id` | texto | `DEVICE_ID` em `secrets.h` |
| `local_id` | texto, 12 caracteres hex | `LOCAL_ID` em `secrets.h`, copiado da tabela `dim_local` |
| `timestamp` | ISO 8601 em UTC | relógio sincronizado por NTP ao conectar no Wi-Fi |
| `velocidade_kmh` | número | CAN/OBD-II ou potenciômetro |
| `frenagem_brusca` | booleano | queda de velocidade acima do limiar entre leituras |

TODO: definir e calibrar na bancada o limiar de `frenagem_brusca` (queda em km/h por segundo).

## Credenciais

Ficam em `secrets.h`, que está no `.gitignore`. Nunca façam commit da senha do Wi-Fi.

```cpp
// embedded/esp32/<projeto>/secrets.h  (não commitar)
#define WIFI_SSID   "nome-da-rede"
#define WIFI_PASS   "senha"
#define MQTT_HOST   "192.168.0.15"
#define MQTT_PORT   1883
#define DEVICE_ID   "bancada-01"
#define LOCAL_ID    "3f2a9c1b7e04"
```

## Ligações previstas

| Componente | Pino do componente | ESP32 |
|---|---|---|
| SN65HVD230 | 3V3 / GND | 3V3 / GND |
| SN65HVD230 | CTX / CRX | GPIO 5 / GPIO 4 |
| Potenciômetro (bancada) | cursor | GPIO 34 (ADC) |

Pinos sugeridos; podem mudar, mas atualizem esta tabela junto com o código.
