# 10 — Plano do MVP, responsáveis e materiais

Fase atual: **construção do MVP** proposto no pitch. A ideação foi concluída e as trilhas
são **Machine Learning** e **Sistemas Embarcados**. O passo a passo completo (tarefas
O1–O2, M1–M7, E1–E11 e I1) está no plano publicado do grupo. Este documento guarda o que
precisa ficar no repositório.

## Resumo da solução

- **Painel da CTTU (ML):** integra as bases públicas de sinistros e mostra trechos e
  horários de maior risco, com score e relatório por trecho.
- **Módulo veicular (Embarcados):** ESP32 + CAN + GPS. Baixa os trechos de risco, lê a
  velocidade (CAN/OBD-II no carro, GPS nas motos) e alerta o motorista com som e luz quando
  ele está acima da velocidade segura num trecho de risco. Publica telemetria via MQTT.
- **O MVP só lê dados e alerta.** Agir sobre o veículo é etapa futura.

Interfaces entre as trilhas: [`09-contrato-trechos-e-telemetria.md`](09-contrato-trechos-e-telemetria.md).

## Como o MVP cobre os requisitos da trilha de ML (`docs/00`)

| Requisito (docs/00) | Onde entra no MVP |
|---|---|
| 1. Sistema embarcado publicando via MQTT + bootstrap dataset | Módulo publica telemetria (docs/09, parte 2); persistida no banco |
| 2. Pipeline orquestrado (Airflow) + EDA | Pipeline CKAN já existente (`scripts/`) vira DAG; EDA dos sinistros |
| 3–6. Baseline, comparação de modelos, tuning, validação cruzada (MLflow) | Modelo de risco por trecho e horário (M4) |
| 7. Inferência integrada ao pipeline | Score recalculado gera o arquivo de trechos servido ao módulo |
| 8. Docker Compose | Mosquitto, PostgreSQL/PostGIS, Airflow, MLflow, API |
| 9. Dashboard consumindo MQTT/API | Painel da CTTU (evolução de `web/`) + estado dos módulos |

Itens 2 a 8 não cabem nas 4 semanas do MVP. O MVP entrega 1, 7 (versão simples) e 9, e
deixa a estrutura pronta para o ciclo de sprints.

## Responsáveis

Preencham na primeira reunião.

| Frente | Tarefas | Pessoas |
|---|---|---|
| Dados e ML | M1 a M4, M7 | |
| API e painel | M5, M6 | |
| Embarcados | E1 a E11 | |
| Integração e pitch | O2, I1 | |

## Materiais

### Temos (laboratório ou grupo)

- [ ] ESP32 DevKit ×2 (um para o módulo, outro para o "carro falso" da bancada CAN)
- [ ] Buzzer ativo 5 V
- [ ] LED RGB ou LEDs verde, amarelo e vermelho
- [ ] Transistor BC547 ou 2N2222
- [ ] Resistores de 220 Ω e 1 kΩ
- [ ] Potenciômetro de 10 kΩ
- [ ] Protoboard, jumpers e cabos USB
- [ ] Multímetro

### Comprar (Mercado Livre, preços de 13/10/2026)

| Item | Qtd | Preço | Pedido feito? | Quem comprou |
|---|---|---|---|---|
| Módulo GPS NEO-6M V2 com antena (Maker Hero) | 1 | R$ 47,90 | [ ] | |
| Módulo CAN SN65HVD230 (RDSCOMP) | **2** | R$ 61,60 | [ ] | |
| Regulador LM2596 step-down, kit com 3 (GAMAFER) | 1 kit | R$ 39,79 | [ ] | |
| **Total** | | **R$ 149,29 + frete** | | |

### Confirmar

- [ ] Cabo OBD-II macho com fios soltos (pigtail): só para o teste em carro real
- [ ] Fusível de linha de 1 a 2 A com porta-fusível

## Cuidados

- Regular o LM2596 para 5,0 V com o multímetro **antes** de ligar o ESP32.
- O GPS dificilmente pega sinal dentro do prédio. Testem ao ar livre ou na janela.
- No carro, o módulo só **lê** dados pelo OBD-II. Nada de enviar comandos ao veículo.
- As ressalvas de `docs/06` continuam valendo para o modelo de risco: o score é calculado
  sobre "chamados", que não batem com os relatórios oficiais, e 2025 é preliminar.
