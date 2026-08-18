# 08 — Fundamentação do tema e oportunidades identificadas

Adendo ao desk research (`01-visao-geral.md`), produzido a partir de pesquisa externa em
18/08/2026 para responder: por que "segurança viária no Recife" é um bom tema, com que
provas, e que oportunidades os dados já catalogados (`02`–`07`) abrem. **Não é ideação de
solução** — isso continua fora de escopo até a semana 5 (ver `01-visao-geral.md`,
`00-contexto-cesar.md`). É munição para justificar o tema e orientar a conversa que vai
acontecer na ideação.

## 1. Escala do problema — e uma tendência que a média nacional esconde

- Pernambuco: 1.828 mortes em sinistros de trânsito em 2024, alta de 12% sobre 2023 — maior
  número desde 2021, revertendo a queda observada entre 2014–2019 ([Diário de Pernambuco,
  05/2026](https://www.diariodepernambuco.com.br/vida-urbana/2026/05/11715268-pernambuco-tem-alta-de-12-nas-mortes-no-transito-em-2024-e-fica-acima-da-media-nacional.html)).
- Recife: 140 mortes no trânsito em 2025, queda geral de 4,8% sobre 2024 ([CBN Recife,
  05/2026](https://www.cbnrecife.com/2026/05/04/a-cada-dois-mortos-no-transito-do-recife-em-2025-um-era-motociclista-aponta-cttu/)).
- Contexto global: a OMS reporta queda de 21% nas mortes no trânsito entre 2011–2025, mas
  ainda 1,16 milhão de mortes/ano no mundo, com meta ODS de reduzir 50% até 2030 frente à
  linha de base de 2021 ([OPAS/OMS,
  07/2026](https://www.paho.org/pt/noticias/21-7-2026-mortes-no-transito-caem-21-globalmente-mas-sao-necessarias-acoes-intensificadas)).

**Leitura**: o total caindo no Recife enquanto sobe por modal (moto, abaixo) é exatamente o
tipo de sinal que se perde no número agregado dos relatórios institucionais e só aparece
olhando o microdado — reforça o argumento de ir além da citação de números do PSVR
(`01-visao-geral.md`).

## 2. Motocicleta como epicentro do problema, não uma categoria a mais

- Recife: motociclistas já são ~56% das mortes no trânsito em 2025, com alta de 11% no ano
  mesmo com o total caindo ([CBN Recife](https://www.cbnrecife.com/2026/05/04/a-cada-dois-mortos-no-transito-do-recife-em-2025-um-era-motociclista-aponta-cttu/);
  [CNF PE](https://www.cnfpe.com.br/2026/05/04/a-cada-duas-mortes-no-transito-do-recife-uma-e-de-um-motociclista-aponta-levantamento-da-cttu/)).
- Brasil: motociclistas são 41,6% das mortes no trânsito; mortes em sinistros de moto
  passaram de 11.182 (2019) para 15.459 (2024), alta de 38% ([Portal do Trânsito — Atlas da
  Violência 2026](https://www.portaldotransito.com.br/noticias/fiscalizacao-e-legislacao/estatisticas/atlas-da-violencia-2026-motociclistas-ja-representam-416-das-mortes-no-transito-no-brasil/)).
- Perfil de vítima em Recife: 84% homens, 60% entre 20–40 anos — faixa etária economicamente
  ativa, o que sustenta um argumento socioeconômico além do de saúde pública ([CBN
  Recife](https://www.cbnrecife.com/2026/05/04/a-cada-dois-mortos-no-transito-do-recife-em-2025-um-era-motociclista-aponta-cttu/)).

## 3. A causa dominante já foi medida — não é hipótese a validar

Recife tem série histórica de monitoramento de velocidade desde 2020, feita pela CTTU com a
Bloomberg Initiative for Global Road Safety (BIGRS), via Johns Hopkins University e UFC:
atualmente 43% das motos ainda trafegam acima do limite, e 75% dos veículos em geral acima da
velocidade considerada segura pela OMS (30–50 km/h) ([Folha
PE](https://www.folhape.com.br/noticias/cttu-inicia-pesquisa-de-monitoramento-da-velocidade-media-e-o/446566/);
[cobertura do estudo
JHU](https://campinas.sp.gov.br/noticias/114843/quase-metade-dos-motociclistas-excedem-velocidade-aponta-estudo-da-johns-hopkins)).
Isso conecta diretamente com os datasets de equipamentos/velocidade já catalogados em
`02-catalogo-de-dados.md` — a causa já está instrumentada nos dados públicos, não precisa ser
descoberta.

## 4. O achado mais importante: a lacuna não é falta de dado, é falta de uma camada aberta

Recife já tem a peça institucional que `03-ontologia.md` diz que falta nos *dados*: existe o
**Compat** (Comitê Municipal de Acidentes de Trânsito), que reúne CTTU, SAMU e Secretaria de
Defesa Social para produzir o Relatório Anual de Segurança Viária — ou seja, alguém já
reconcilia manualmente bases que, nos dados abertos, não compartilham chave de junção ([CBN
Recife sobre o relatório
anual](https://www.cbnrecife.com/artigo/relatorio-anual-de-seguranca-viaria-realizado-pela-cttu-aponta-reducao-nas-mortes-de-transito-no-recife)).
O PSVR também tem um eixo formal de "Gestão de Dados", que alimenta continuamente os eixos de
fiscalização, engenharia viária e educação/comunicação ([CTTU — Gestão de dados do
Recife](https://cttu.recife.pe.gov.br/gestao-de-dados-do-recife)).

**Reenquadramento**: não é "a prefeitura não usa dado" — é "existe um processo institucional
de integração de dados que roda de forma manual/fechada, e os dados abertos que alimentam
esse processo estão públicos mas desconectados entre si" (consistente com
`06-limitacoes-metodologicas.md`, item 6). A oportunidade é uma camada aberta e sistemática
que se aproxime do que o Compat já faz à mão — não substituí-lo, instrumentá-lo.

## 5. Referência externa de para onde essa camada poderia apontar

Cidades com programas Vision Zero data-driven publicam camadas derivadas do dado bruto, não
só o dado em si:

- **San Diego (SANDAG)**: o *Safety Focus Network* identifica que 6% da malha viária
  concentra 54% dos sinistros graves/fatais ([the-atlas.com](https://the-atlas.com/projects/achieving-vision-zero--reducing-traffic-fatalities-using-smart-data-and-analytics-4)).
- **Nova York**: o *Crash & Interventions Map* cruza sinistro com intervenção de engenharia
  realizada ([Microsoft NY
  blog](https://blogs.microsoft.com/newyork/2017/06/29/vision-zero-labs-using-data-science-to-improve-traffic-safety/)).

Ambos dependem do mesmo tipo de cruzamento espacial (sinistro × equipamento/via por
proximidade geográfica) que `06-limitacoes-metodologicas.md` (item 7) já identifica como
possível para Recife, mas dependente de geocodificação prévia e validação manual de amostra.

## 6. Para pensar na ideação (semana 5) — não é decisão

Um caminho de solução a considerar, dado o que os dados de Recife já oferecem (sinistros sem
geo, mas equipamentos/semáforos com lat/long; série de velocidade desde 2020; moto como causa
dominante): priorização de vias por risco, combinando sinistro + velocidade monitorada +
equipamento de fiscalização, com recorte em motocicletas. Isso também sugere uma variável-alvo
defensável para a trilha de Aprendizagem de Máquina citada em `00-contexto-cesar.md` — risco
por segmento de via (proxy: contagem de sinistros/feridos por segmento), não previsão de
sinistro individual —, o que ajudaria a responder a pergunta bloqueante sobre se o tema tem
variável-alvo viável sem precisar de trilha customizada.

## Fontes

- [CBN Recife — A cada dois mortos no trânsito do Recife em 2025, um era motociclista, aponta CTTU](https://www.cbnrecife.com/2026/05/04/a-cada-dois-mortos-no-transito-do-recife-em-2025-um-era-motociclista-aponta-cttu/)
- [CNF PE — cobertura do mesmo levantamento da CTTU](https://www.cnfpe.com.br/2026/05/04/a-cada-duas-mortes-no-transito-do-recife-uma-e-de-um-motociclista-aponta-levantamento-da-cttu/)
- [Portal do Trânsito — Atlas da Violência 2026](https://www.portaldotransito.com.br/noticias/fiscalizacao-e-legislacao/estatisticas/atlas-da-violencia-2026-motociclistas-ja-representam-416-das-mortes-no-transito-no-brasil/)
- [Diário de Pernambuco — Pernambuco tem alta de 12% nas mortes no trânsito em 2024](https://www.diariodepernambuco.com.br/vida-urbana/2026/05/11715268-pernambuco-tem-alta-de-12-nas-mortes-no-transito-em-2024-e-fica-acima-da-media-nacional.html)
- [OPAS/OMS — Mortes no trânsito caem 21% globalmente](https://www.paho.org/pt/noticias/21-7-2026-mortes-no-transito-caem-21-globalmente-mas-sao-necessarias-acoes-intensificadas)
- [Folha PE — CTTU inicia pesquisa de monitoramento da velocidade média](https://www.folhape.com.br/noticias/cttu-inicia-pesquisa-de-monitoramento-da-velocidade-media-e-o/446566/)
- [Prefeitura de Campinas — cobertura do estudo Johns Hopkins sobre velocidade de motociclistas](https://campinas.sp.gov.br/noticias/114843/quase-metade-dos-motociclistas-excedem-velocidade-aponta-estudo-da-johns-hopkins)
- [CBN Recife — Relatório Anual de Segurança Viária e o papel do Compat](https://www.cbnrecife.com/artigo/relatorio-anual-de-seguranca-viaria-realizado-pela-cttu-aponta-reducao-nas-mortes-de-transito-no-recife)
- [CTTU — Gestão de dados do Recife](https://cttu.recife.pe.gov.br/gestao-de-dados-do-recife)
- [the-atlas.com — Achieving Vision Zero, Reducing Traffic Fatalities (San Diego/SANDAG)](https://the-atlas.com/projects/achieving-vision-zero--reducing-traffic-fatalities-using-smart-data-and-analytics-4)
- [Microsoft New York blog — Vision Zero Labs: Using Data Science to Improve Traffic Safety](https://blogs.microsoft.com/newyork/2017/06/29/vision-zero-labs-using-data-science-to-improve-traffic-safety/)
