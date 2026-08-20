# Claim ledger

Registro único de tudo que este harness afirma saber. Artefato que cita fato cita daqui.

## Formato

```
### C-nn — <afirmação em uma linha>
tipo:       fato | estimativa | lacuna
confianca:  alta | media | baixa
status:     proposto | confirmado | rebaixado | refutado
fonte:      <URL + data de acesso>  (ou: queries rodadas, se tipo=lacuna)
evidencia:  <o que exatamente a fonte diz — paráfrase, não cópia>
decisao:    <qual pergunta de 00-questions este claim serve>
contestacao: <o que o adversary tentou e o que sobrou>
```

Regras:
- ID nunca é reciclado. Claim refutado fica no arquivo com status `refutado`.
- Claim que muda de conteúdo vira ID novo, com `substitui: C-nn`.
- `confianca` sem data de acesso é inválida.

---

## Seed — claims herdados de `../../docs/06` e `../../docs/08`

Estes já tinham fonte citada no desk research, mas entram como `proposto` porque ainda não
passaram pela contestação deste harness — exceto `C-02`, que `docs/08` já verificou e a fonte
não sustentou.

### C-01 — Recife (CTTU) tem um eixo formal de "Gestão de Dados" dentro do PSVR
tipo: fato
confianca: media
status: proposto
fonte: CTTU — Gestão de dados do Recife, https://cttu.recife.pe.gov.br/gestao-de-dados-do-recife — acessado 18/08/2026 (via `../../docs/08-fundamentacao-e-oportunidades.md`, seção 4)
evidencia: página institucional descreve um eixo de gestão de dados que alimenta continuamente os eixos de fiscalização, engenharia viária e educação/comunicação do PSVR
decisao: D1 (Q1.2) — ponto de partida para perguntar se esse eixo já faz algo preditivo ou só consolida indicadores
contestacao: tentativa feita — busquei artigo acadêmico independente ("Cidades inteligentes e mobilidade urbana... Recife/PE", Revista de Gestão e Secretariado) que citava o tema; bloqueado por erro 403 ao tentar ler o texto completo. Mantido `proposto` — nenhuma fonte independente da própria CTTU foi lida com sucesso ainda

### C-02 — A existência de um comitê "Compat" (CTTU + SAMU + Defesa Social) que reconcilia dados de sinistro
tipo: lacuna
confianca: baixa
status: rebaixado
fonte: tentativa de verificação registrada em `../../docs/08-fundamentacao-e-oportunidades.md`, seção 4 (checagem em 08/2026) — a matéria da CBN Recife originalmente citada é de 08/03/2022, sobre o relatório 2017–2020, e não menciona "Compat" nem SAMU/Defesa Social; a página oficial do PSVR também estava inacessível na tentativa de confirmação
evidencia: a afirmação nasceu de conversa, não de fonte direta, e não sobreviveu à checagem
decisao: D2 (Q2.1) — não perguntar "como funciona o Compat" (pressupõe que existe); perguntar se existe algo equivalente, sem nomear
contestacao: já contestado em `docs/08` — fonte não sustenta o claim; mantido como lacuna, não deletado

### C-03 — CTTU mede velocidade das vias desde 2020, em parceria com BIGRS/Johns Hopkins University/UFC, para avaliar se políticas de segurança viária já implementadas são suficientes
tipo: fato
confianca: media
status: confirmado
fonte: Folha PE, https://www.folhape.com.br/noticias/cttu-inicia-pesquisa-de-monitoramento-da-velocidade-media-e-o/446566/ — acessado 18/08/2026 (via `../../docs/08`, seção 3); confirmado de forma convergente por Portal de Prefeitura e ONSV (Observatório Nacional de Segurança Viária), acessados 20/08/2026
evidencia: 3 fontes independentes convergem: monitoramento contínuo desde 2020, com BIGRS/JHU/UFC, usado para "estabelecer um comparativo anual e analisar se as políticas implementadas... são suficientes" — ou seja, é avaliação retrospectiva de política já existente, não previsão de impacto de mudança futura
decisao: D1 (Q1.3) — RESPONDE parcialmente: o uso confirmado é retrospectivo/avaliativo, não preditivo. Ainda não sabemos se o mesmo dado também alimenta decisão prévia de nova intervenção — isso continua em aberto pra entrevista
contestacao: 3 fontes independentes convergem no mesmo uso (avaliação retrospectiva); não rebaixado, mas o escopo do "pra que serve" ficou mais preciso que a versão seed

### C-04 — Cidades com programas Vision Zero data-driven publicam camadas analíticas derivadas do dado bruto (não simulação preditiva)
tipo: fato
confianca: media
status: proposto
fonte: the-atlas.com (SANDAG Safety Focus Network) — acessado 18/08/2026; blogs.microsoft.com/newyork (NYC Crash & Interventions Map) — acessado 18/08/2026 (ambos via `../../docs/08`, seção 5)
evidencia: SANDAG identifica que 6% da malha viária concentra 54% dos sinistros graves/fatais; NYC cruza sinistro com intervenção de engenharia já realizada. Nenhum dos dois é um "digital twin" de simulação preditiva — são camadas analíticas retrospectivas sobre dado histórico
decisao: D3 (Q3.2) — benchmark pra perguntar se uma camada assim (não necessariamente simulação) já resolveria algo pra quem decide hoje
contestacao: pendente — risco de a entrevista confundir "camada analítica retrospectiva" com "simulação preditiva/digital twin"; são conceitos diferentes, não misturar nas perguntas (ver nota em Q3.1 vs Q3.2)

## D1 — consolidado a partir do scout de Q1.1 (20/08/2026)

### C-05 — Nenhuma página institucional da CTTU descreve publicamente uma metodologia de previsão de impacto ou simulação de tráfego para mudança de sinalização/semáforo
tipo: lacuna
confianca: baixa
status: refutado
fonte: `research/sources/cttu-institucional-estudos-mobilidade.md` (acessado 20/08/2026) + `research/sources/cttu-estudos-fiscalizacao-eletronica.md` (acessado 20/08/2026); refutado por `research/sources/recife-semaforos-inteligentes-2024.md` (ver `[C-09]`)
evidencia: as duas páginas institucionais originais de fato não mencionam metodologia, mas existe cobertura de imprensa extensa e convergente (3 veículos independentes) sobre um programa concreto de "semáforos inteligentes" com ajuste automático via análise de tráfego em tempo real, ativo desde 07/2024
decisao: D1 (Q1.1) — a lacuna não se sustenta: existe, sim, tecnologia de ajuste automático de sinalização publicamente documentada (só não nas duas páginas institucionais que o scout olhou primeiro)
contestacao: refutado — busca em pt-BR por "semáforos inteligentes Recife" achou o programa que a busca original (focada em "previsão"/"simulação") não achou; erro do scout foi de vocabulário de busca, não de existência do fato

### C-06 — A função de resposta a incidente da Central de Operação e Trânsito (COT) é monitoramento por câmera + despacho de equipe em tempo real; isso NÃO significa que a CTTU não tenha nenhuma tecnologia de ajuste automático de semáforo
tipo: fato
confianca: media
status: rebaixado
fonte: `research/sources/cttu-central-operacao-transito.md` — acessado 20/08/2026 (função da COT); `research/sources/recife-semaforos-inteligentes-2024.md` — acessado 20/08/2026 (contraexemplo que limita a generalização)
evidencia: a descrição da COT como câmera+despacho continua de pé (não foi contestada diretamente), mas a inferência mais ampla que o claim original sugeria — "CTTU não tem nada preditivo/adaptativo" — é falsa: o programa de semáforos inteligentes (`[C-09]`) é uma iniciativa distinta da COT, com ajuste automático real
decisao: D1 (Q1.1, Q1.4) — rebaixado de escopo: vale só para a função específica de resposta a incidente da COT, não pode ser citado no roteiro como "a CTTU é puramente reativa"
contestacao: contestado — a fonte original (CTTU falando de si mesma) era sobre um serviço específico (COT), e o claim tinha generalizado demais a partir dela; ID mantido, escopo reduzido

### C-07 — Existe obrigação regulatória (Resolução CONTRAN 798/2020) de Levantamento Técnico bienal e Estudo Técnico anual para fiscalização eletrônica de velocidade, com conteúdo do estudo não publicado na página da CTTU que o indexa
tipo: fato
confianca: media
status: confirmado
fonte: `research/sources/cttu-estudos-fiscalizacao-eletronica.md` (acessado 20/08/2026); teor da resolução confirmado de forma convergente por 3 fontes jurídicas independentes (qconcursos, tecconcursos, legisweb), acessadas 20/08/2026
evidencia: as 3 fontes jurídicas convergem: Levantamento Técnico bienal (controladores fixos) e Estudo Técnico anual (redutores em trechos críticos), aprovação Inmetro, e obrigação de disponibilizar ao público — mas nenhuma delas, nem a página da CTTU, descreve o conteúdo real do estudo (é levantamento de campo? modelagem preditiva?)
decisao: D1 — mostra que existe processo formal para pelo menos um tipo de intervenção (fiscalização eletrônica); não confirma se sinalização/semáforo segue processo equivalente — são intervenções diferentes, não assumir que uma generaliza pra outra
contestacao: confirmado quanto à existência e periodicidade da obrigação (3 fontes independentes convergem); o conteúdo interno do estudo continua não verificado — os PDFs linkados na página da CTTU não foram abertos nesta rodada

### C-08 — Controle adaptativo de semáforo via IA, rodando continuamente em operação real (não só piloto acadêmico), existe em pelo menos duas iniciativas documentadas fora do Brasil (Surtrac/Pittsburgh, produto comercial Miovision Adaptive)
tipo: fato
confianca: baixa
status: rebaixado
fonte: busca de contestação — "adaptive traffic signal control system deployed production city real-time AI operational not pilot", acessado 20/08/2026 (resumo de busca; páginas de fabricante/produto, não paper peer-reviewed nem reportagem independente lida por inteiro)
evidencia: Surtrac (Pittsburgh) reporta redução de 25% no tempo de viagem e 40% no tempo de espera em operação real desde a implantação inicial; Miovision Adaptive é descrito como produto comercial implantado "not pilot". Isso contradiz a leitura original (C-08 seed) de que só existiria simulação pontual, não IA contínua em operação
decisao: D1, D3 (Q3.1, Q3.2) — a distinção relevante pra entrevista não é "existe vs. não existe tecnologia de ajuste automático" (existe, em várias cidades, inclusive Recife desde 2024 — ver `[C-09]`), é "ajusta ao tráfego atual em tempo real" vs. "prevê o impacto de uma mudança futura antes de implementá-la" — a segunda continua sem exemplo operacional confirmado nesta pesquisa
contestacao: rebaixado — claim original generalizou de menos (só achou simulação pontual) para mais (afirmou que IA contínua "não" existe em prática); fontes de contestação são material de fabricante/produto (Econolite, Miovision), que tem interesse comercial em superestimar resultado — por isso a confiança permanece baixa mesmo depois de rebaixado, não sobe

### C-09 — Recife tem semáforos com controle adaptativo em tempo real (ajuste automático de ciclo por análise de tráfego via câmeras) em operação desde 07/2024, em 2 corredores
tipo: fato
confianca: media
status: confirmado
fonte: `research/sources/recife-semaforos-inteligentes-2024.md` — Diário de Pernambuco, CBN Recife e Tribuna Online, acessados 20/08/2026, todos citando a mesma nota da Prefeitura/CTTU de 05/07/2024
evidencia: R$ 1,07 milhão investidos; avenidas Antônio de Góes (corredor completo) e Abdias de Carvalho (trecho Chesf–Estádio); ~140 mil veículos/dia; sistema de câmeras que "conversam entre si" e ajustam o tempo de ciclo a partir do tráfego observado em tempo real — não é previsão de impacto de mudança futura, é adaptação ao presente
decisao: D1 (Q1.1, Q1.5) — RESPONDE Q1.5 diretamente: sim, existe tecnologia de ajuste automático (controle adaptativo), documentada publicamente, em pelo menos 2 corredores desde 2024. Não responde Q1.1 na forma original (previsão de impacto *antes* de implementar uma mudança) — essa parte continua em aberto pra entrevista
contestacao: 3 fontes de imprensa independentes entre si (mesma nota oficial, mas veiculada por 3 redações distintas, sem contradição entre elas) — não refutado; confiança fica em `media`, não `alta`, porque o evento tem mais de 12 meses (07/2024) e não há confirmação de que o programa segue ativo/foi expandido em 2026
