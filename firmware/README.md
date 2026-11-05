# Firmware do módulo veicular (ESP32)

Trilha Sistemas Embarcados. Tarefas E1 a E11 (ver `docs/10-plano-mvp-e-materiais.md`).

O módulo:

1. baixa os trechos de risco de `GET /modulo/trechos` e guarda na flash (LittleFS);
2. lê posição (GPS NEO-6M) e velocidade (CAN/OBD-II, GPS ou potenciômetro na bancada);
3. decide o alerta (verde, amarelo ou vermelho com bipe);
4. publica telemetria via MQTT.

Formatos de entrada e saída: `docs/09-contrato-trechos-e-telemetria.md`.
Enquanto a API não estiver na rede, use uma cópia de `data/contrato/trechos_exemplo.json`.

## Credenciais

Ficam em `secrets.h`, que está no `.gitignore`. Nunca façam commit da senha do Wi-Fi.

```cpp
// firmware/<projeto>/secrets.h  (não commitar)
#define WIFI_SSID   "nome-da-rede"
#define WIFI_PASS   "senha"
#define API_URL     "http://192.168.0.15:8000/modulo/trechos"
#define MQTT_HOST   "192.168.0.15"
#define MQTT_PORT   1883
#define MODULO_ID   "bancada-01"
```

## Ligações previstas

| Componente | Pino do componente | ESP32 |
|---|---|---|
| SN65HVD230 | 3V3 / GND | 3V3 / GND |
| SN65HVD230 | CTX / CRX | GPIO 5 / GPIO 4 |
| NEO-6M | VCC / GND | 3V3 / GND |
| NEO-6M | TX / RX | GPIO 16 (RX2) / GPIO 17 (TX2) |
| Buzzer (via BC547) | base, com resistor de 1 kΩ | GPIO 25 |
| LED verde / amarelo / vermelho | com resistor de 220 Ω | GPIO 26 / 27 / 14 |
| Potenciômetro (bancada) | cursor | GPIO 34 (ADC) |

Pinos sugeridos; podem mudar, mas atualizem esta tabela junto com o código.
