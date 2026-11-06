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

## D1 — velocidade segura (22/10/2026)

### C-10 — A OMS define velocidade segura por tipo de conflito: 30 km/h (carro × pedestre/ciclista), 50 km/h (interseção com colisão lateral), 70 km/h (colisão frontal), 100 km/h (sem conflito lateral/frontal); motociclistas têm limiar parecido com o de pedestres
tipo: fato
confianca: alta
status: confirmado
fonte: `research/sources/oms-speed-management-2023.md` — OMS/GRSP/FIA/Banco Mundial, Speed management, 2ª ed., 2023, Tabela 1 p. 4 e p. 3, acessado 22/10/2026
evidencia: tabela lida no PDF oficial da OMS (não em resumo de terceiro)
decisao: D1 (Q1.6) — referência externa pra perguntar qual parâmetro a CTTU usa, sem pressupor que seja este
contestacao: tentei derrubar por dois lados. (1) Origem: a busca inicial atribuía os valores 30/50/70 à OCDE, não à OMS; o PDF da OMS tem a tabela, citando fontes próprias (4, 5) — sobreviveu. (2) Versão do desk research: `../../docs/08` dizia "OMS: 30–50 km/h" a partir da Folha PE; a fonte primária não dá uma faixa única, e sim um valor por tipo de conflito — a versão de `docs/08` fica corrigida em `../../docs/13-velocidade-segura.md`, não o claim. Confiança `alta`: fonte primária, publicada há menos de 3 anos, lida hoje

### C-11 — O PSVR 2026–2036 (Iniciativa 4.3) prevê readequar limites de velocidade "de acordo com parâmetros seguros" sem definir quais são, e lista "análise e simulação de impacto no trânsito" no estudo técnico prévio, sob a SEOPS-CTTU
tipo: fato
confianca: media
status: confirmado
fonte: `research/sources/psvr-iniciativa-4-3-velocidade.md` — texto extraído do PDF oficial do PSVR neste repo, relido em 22/10/2026
evidencia: objetivo e ações da Iniciativa 4.3 lidos no texto; nenhuma ocorrência de "km/h" no texto extraído inteiro do PSVR
decisao: D1 (Q1.6 e, indiretamente, Q1.1 — "simulação de impacto" aparece como ação planejada, não como prática existente); D2 (Q2.2 — SEOPS-CTTU como responsável pela 4.3)
contestacao: risco de a ausência ser artefato da extração (valor numa tabela-imagem que o pdfplumber não lê). A busca foi no texto inteiro e o objetivo da 4.3 foi lido diretamente, mas não abri o PDF página a página — por isso `media`, não `alta`. Também não se pode ler "parâmetros seguros" como sinônimo de C-10: o PSVR não cita a tabela da OMS (cita a OMS só pelo Global Status Report 2023 nas referências)

### C-12 — A lei municipal do Plano de Mobilidade Urbana do Recife (art. 34) fixaria 50 km/h como máximo para vias arteriais e 60 km/h para as de trânsito rápido
tipo: fato
confianca: media
status: proposto
fonte: `research/sources/recife-plano-mobilidade-limites-velocidade.md` — Diário de Pernambuco (31/07/2026) e Folha PE, acessados 22/10/2026, citando a lei municipal (não lida)
evidencia: imprensa atribui ao art. 34 o limite de 50 km/h nas arteriais (base da redução da Av. Boa Viagem de 60 para 50 km/h); minuta de 2018 trazia 60/50/40/30 km/h por classe viária
decisao: D1 (Q1.6) — se confirmado, Recife já tem um limite legal municipal mais baixo que o padrão do CTB (60 km/h nas arteriais) e igual ao limiar de colisão lateral da OMS ([C-10])
contestacao: não sobe para `confirmado`. (1) Número da lei e texto final do art. 34 não localizados. (2) Uma emenda ao PL 42/2021 trata o art. 34 como critério de travessia de pedestre, não de velocidade — pode ser renumeração na tramitação ou erro da imprensa. (3) Duas matérias, provavelmente da mesma nota da CTTU, não são duas fontes independentes (ver `../../docs/06` #10). Para confirmar: ler a lei no SAPL da Câmara do Recife ou no Diário Oficial

### C-13 — Não se sabe qual referência técnica a CTTU usa para definir "velocidade segura" / "parâmetros seguros" nem quais vias estão em cada classe viária
tipo: lacuna
confianca: baixa
status: proposto
fonte: buscas em 22/10/2026 — `grep -i "km/h\|velocidade segura\|limite de velocidade"` em `../../data/processed/pdf/` (PSVR e Relatórios Anuais 2020–2024) e `../../docs/`; web: "CTTU Recife readequação limites de velocidade estudo técnico 2026", "Lei municipal Recife Plano de Mobilidade Urbana 2021 art. 34 velocidade máxima vias arteriais 50 km/h"
evidencia: os Relatórios Anuais só citam 30 km/h (e 20 km/h no Jardim Monte Verde) em intervenções pontuais; o PSVR não define o parâmetro ([C-11]); o limite municipal está só na imprensa ([C-12]); nenhuma das bases de dados abertas baixadas traz a classificação viária
decisao: D1 (Q1.6)
contestacao: lacuna de busca, não afirmação sobre a CTTU — a referência pode existir em documento interno, no estudo técnico exigido pela CONTRAN 798/2020 ([C-07]) ou no Manual de Desenho de Ruas do Recife (2023, citado no Relatório 2022), que não foi lido
