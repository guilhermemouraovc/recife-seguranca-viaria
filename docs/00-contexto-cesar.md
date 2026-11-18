# 00 — Contexto acadêmico (CESAR School, Projeto 6)

Contexto de curso/processo — não confundir com o modelo de dados (`03-ontologia.md`). Fonte:
slides da disciplina compartilhados pelo grupo.

## Onde estamos (em 18/08/2026)

- Cursando a **semana 2** (entrega era semana passada, atrasada). Apresentação da semana 2 é
  **quinta-feira**.
- Entrega da **semana 3** é **sexta-feira** (dia seguinte).
- Estamos na fase de "Escolha do tema e desk research" → "Pesquisa com usuário e requisitos".
  Ainda **não entramos em ideação de solução** (isso só acontece na semana 5).

## Estrutura do semestre (marcos que afetam prazo)

| Semana | Entrega | Pontos |
|---|---|---|
| 1 | Onboarding, definição de grupos | — |
| 2 | Escolha do tema e desk research (dados secundários) | 1pt |
| 3–4 | Pesquisa com usuário e requisitos (dados primários) | 1pt cada |
| 5 | **Ideação e definição do projeto** — envio da proposta (sexta, 4/set) | 3pts |
| 6 | Avaliação das propostas pelos orientadores | — |
| 7 | Feedback e ajustes de planejamento | — |
| 8 | **SR1** — backlog + planejamento semanal | 4pts |
| 9 | Notas e feedback do SR1 | — |
| 10–17 | Ciclo de desenvolvimento (sprints) | 1pt/semana |
| 18 | Preparação para o SR2 | — |
| 19 | **SR2** — apresentação dos resultados | 2pts |

**FACT**: autoavaliação de equipe liberada 72h antes de SR1/SR2; quem não enviar até 23:59 do
dia do SR tira zero no FACT.

## Trilha técnica: grupo é só de Ciência da Computação → segue trilha de Aprendizagem de Máquina

O grupo, sendo composto só por estudantes de CC, **deve seguir os requisitos técnicos de
Aprendizagem de Máquina**, a menos que apresente uma justificativa para pedir uma trilha
customizada (com requisitos alternativos, sujeitos a aprovação). **Isso ainda não foi
decidido para este projeto** — ver `07-backlog-tarefas.md`/decisão pendente.

Isso muda o escopo real do projeto: os documentos `01`–`07` deste repositório cobrem hoje
**só a etapa de extração/organização de dados** (pipeline de ingestão CKAN). Se a trilha de
ML for mantida sem pedido de customização, o projeto completo (não só esta etapa) também vai
precisar, ao longo do semestre, de:

1. Infraestrutura de aquisição de dados com sistema embarcado (físico ou simulado) publicando
   via **MQTT**, persistido em armazenamento adequado — **bootstrap dataset**.
2. Pipeline de dados orquestrado com **Apache Airflow** (ingestão, preparação, disponibilização
   para treino) + notebook de EDA e justificativa das decisões de preparação.
3. Modelo baseline (KNN, regressão linear/logística, árvore) com métricas registradas em
   **MLflow**.
4. Comparação de ≥3 modelos com métricas, visualizações (matriz de confusão, ROC/AUC, erros) e
   análise crítica.
5. Otimização de hiperparâmetros (Grid/Random Search ou Optuna) documentada, registrada no
   MLflow.
6. Validação cruzada (k-fold/stratified) com discussão de overfitting/underfitting e
   generalização.
7. Integração do modelo ao pipeline (inferência automática sobre novos dados do sistema
   embarcado/simulador).
8. Conteinerização completa via **Docker Compose** (broker MQTT, banco, Airflow, MLflow, API
   etc.) — solução sobe com um único comando.
9. Dashboard integrado consumindo MQTT/API, mostrando indicadores, inferências do modelo e
   saúde da solução em tempo de execução.
10. Apresentação final demonstrando a arquitetura ponta a ponta, com justificativa técnica e
    discussão de limitações.

**Implicação para este repositório**: o pipeline de extração de dados abertos (CTTU/SAMU) que
os docs `01`–`07` descrevem cobre bem os itens 1–2 acima (dado estático em vez de sistema
embarcado real — precisa decidir se serve como "simulador"), mas os itens de ML (3–7),
conteinerização (8) e dashboard (9) **ainda não têm nenhum plano** neste conjunto de
documentos. Antes de avançar para ideação (semana 5), vale confirmar com orientador se:

- a trilha de ML será seguida à risca, ou se o grupo vai pedir trilha customizada com
  justificativa (o problema de segurança viária pode não ter uma variável-alvo óbvia para
  ML supervisionado sem mais pesquisa de requisitos);
- os dados abertos da CTTU/SAMU (batch, históricos) podem substituir o "sistema embarcado
  publicando via MQTT" exigido no CC 1, ou se isso é um requisito literal de hardware/streaming.

Essas duas perguntas são **bloqueantes para a proposta de projeto da semana 5**, não para o
trabalho atual desta etapa (extração de dados), que segue como planejado em `01`–`07`.
