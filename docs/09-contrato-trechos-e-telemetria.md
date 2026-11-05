# 09 — Contrato dos trechos de risco e da telemetria do módulo

Este é o formato que a trilha de ML entrega e que o ESP32 consome. As duas trilhas
trabalham em cima dele, então **qualquer mudança aqui precisa ser combinada entre as duas**
e o campo `versao` deve ser incrementado.

- Arquivo de exemplo: [`data/contrato/trechos_exemplo.json`](../data/contrato/trechos_exemplo.json)
- Validador: `python scripts/validar_trechos.py data/contrato/trechos_exemplo.json`
- Endpoint que entrega o arquivo ao módulo: `GET /modulo/trechos` (pasta `api/`)
- Situação: **proposta**, a fechar entre as trilhas na semana 0 (tarefa O2)

Este documento define as duas interfaces entre as trilhas:

1. **Trechos de risco** (ML → módulo): o que o modelo entrega e o ESP32 baixa por HTTP.
2. **Telemetria** (módulo → plataforma): o que o ESP32 publica via MQTT.

# Parte 1 — Trechos de risco

## Estrutura

```json
{
  "versao": 1,
  "gerado_em": "2026-10-13T12:00:00-03:00",
  "fonte": "exemplo-manual",
  "trechos": [
    {
      "id": "derby",
      "nome": "Praça do Derby",
      "lat": -8.05678,
      "lon": -34.89953,
      "raio_m": 120,
      "risco": "alto",
      "score": 0.86,
      "horas": [7, 8, 17, 18, 19],
      "vel_segura": 30
    }
  ]
}
```

## Campos

| Campo | Tipo | Regra | Para que serve |
|---|---|---|---|
| `versao` | inteiro | ≥ 1 | O ESP32 recusa versões que não conhece |
| `gerado_em` | texto ISO 8601 | com fuso (-03:00) | Saber se a cópia guardada no módulo está velha |
| `fonte` | texto | ex.: `exemplo-manual`, `modelo-v1` | Rastrear de onde veio o arquivo |
| `trechos` | lista | até 200 itens | Limite para caber na memória do ESP32 |
| `id` | texto | minúsculas, números e hífen; único | Identificar o trecho no painel e nos logs |
| `nome` | texto | até 60 caracteres | Exibir no painel e no relatório |
| `lat`, `lon` | número | dentro da região do Recife | Centro do trecho (graus decimais, WGS84) |
| `raio_m` | inteiro | 20 a 500 | O módulo considera "dentro do trecho" quando a distância ao centro ≤ raio |
| `risco` | texto | `baixo`, `medio` ou `alto` | Nível mostrado no painel e usado no alerta |
| `score` | número | 0 a 1 | Valor bruto do modelo (o `risco` é a faixa desse score) |
| `horas` | lista de inteiros | 0 a 23; **lista vazia = vale o dia todo** | Horários em que o trecho é de risco |
| `vel_segura` | inteiro (km/h) | 10 a 80 | Acima disso, dentro do trecho e no horário, o alerta fica vermelho |

## Faixas de risco (proposta, a validar com a CTTU)

| `score` | `risco` |
|---|---|
| < 0,40 | `baixo` |
| 0,40 a 0,69 | `medio` |
| ≥ 0,70 | `alto` |

## Velocidade segura (proposta)

O modelo de ML calcula **risco**, não o limite da via. A regra inicial é:

- `vel_segura` = limite da via (dados de velocidade da CTTU ou tipo de via)
- se `risco` = `alto`: `vel_segura` = limite − 10 km/h (mínimo de 20 km/h)

## Comportamento esperado do módulo

| Situação | Alerta |
|---|---|
| Fora de qualquer trecho, ou trecho fora do horário | Verde, sem som |
| Dentro do trecho, no horário, velocidade ≤ `vel_segura` | Amarelo, sem som |
| Dentro do trecho, no horário, velocidade > `vel_segura` | Vermelho + bipe curto |

Se dois trechos se sobrepõem, vale o de maior `score`.

## Observações

- O arquivo de exemplo usa locais citados pela CTTU na entrevista, com coordenadas do
  Google Maps. **Score, risco, horários e velocidade segura são inventados** para teste;
  os valores reais virão do modelo (tarefa M4).
- Rua Dez de Julho: o ponto usado é o de Boa Viagem. Confirmar com a CTTU se é o trecho
  da intervenção. Estrada Velha de Água Fria: é uma via longa, então o ponto exato do
  radar instalado em 11/2021 também precisa ser confirmado.
- Os nomes de campo são curtos de propósito, para economizar memória no ESP32.

# Parte 2 — Telemetria do módulo via MQTT

Os requisitos da trilha de ML (`docs/00-contexto-cesar.md`, item 1) pedem um sistema
embarcado publicando via **MQTT**, com os dados persistidos (o "bootstrap dataset").
O módulo cumpre isso publicando o que ele lê e decide.

## Tópicos

| Tópico | Quando | Retido? |
|---|---|---|
| `p6g3/modulo/<modulo_id>/telemetria` | a cada 1 s em movimento, a cada 10 s parado | não |
| `p6g3/modulo/<modulo_id>/alerta` | só quando o nível de alerta muda | não |
| `p6g3/modulo/<modulo_id>/status` | ao conectar (`online`) e como last will (`offline`) | sim |

`<modulo_id>`: minúsculas e hífen, ex.: `bancada-01`, `carro-marina`.
QoS 0 para telemetria, QoS 1 para alerta e status.

## Payload de telemetria

```json
{
  "ts": "2026-10-13T18:05:12-03:00",
  "lat": -8.05678,
  "lon": -34.89953,
  "vel": 42,
  "fonte_vel": "can",
  "trecho": "derby",
  "alerta": "vermelho",
  "versao_trechos": 1
}
```

| Campo | Tipo | Regra |
|---|---|---|
| `ts` | texto ISO 8601 | com fuso; vindo do GPS (o ESP32 não tem relógio confiável) |
| `lat`, `lon` | número | `null` se o GPS ainda não tem posição |
| `vel` | inteiro km/h | velocidade usada na decisão |
| `fonte_vel` | texto | `can`, `gps` ou `sim` (potenciômetro/bancada) |
| `trecho` | texto ou `null` | `id` do trecho em que está, ou `null` |
| `alerta` | texto | `verde`, `amarelo` ou `vermelho` |
| `versao_trechos` | inteiro | `versao` do arquivo de trechos carregado |

O payload de `alerta` é o mesmo da telemetria, publicado no instante da mudança.

## Cuidados

- `fonte_vel = "sim"` marca dado de bancada. Ele **não** deve ser misturado com dado real
  em análises, nem apresentado como medição de rua.
- Telemetria de veículo real tem posição de uma pessoa identificável (quem dirigia).
  Guardem só o necessário e não publiquem esse dado em lugar aberto.
