# Literatura internacional — sinalização/semáforo preditivo (panorama geral, não específico de Recife)

- **URLs:** https://www.nature.com/articles/s41598-025-13694-w (Scientific Reports, paywall —
  não foi possível ler o texto completo, só o resumo indexado pela busca);
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10255577/ (Snake Optimization Algorithm para timing
  de semáforo via vídeo)
- **Data de acesso:** 20/08/2026
- **Publicado por:** periódicos acadêmicos com revisão por pares (Scientific Reports/Nature;
  PMC/NCBI)
- **Interesse da fonte:** acadêmico — sem interesse comercial direto, mas artigos de otimização
  tendem a reportar resultado favorável ao próprio método proposto
- **Pergunta relacionada:** Q3.1, Q3.2 (background pra formular a pergunta sobre "digital twin")

## O que a busca indica (paráfrase, resumo de ferramenta de busca — não li o texto completo do
primeiro artigo por estar atrás de paywall)

Existe literatura acadêmica ativa (2025) sobre semáforos com timing ajustado por previsão de
fluxo (dados históricos + tempo real: acidente, clima, evento) usando aprendizado de máquina,
e sobre otimização de timing via visão computacional (contagem de veículo por vídeo + algoritmo
de otimização), testados por simulação/exemplo empírico controlado — não encontrei, nesta
rodada, relato de adoção operacional em produção por um órgão de trânsito municipal real (só
Erzurum/Turquia, Toronto, Denpasar/Indonésia e Glasgow apareceram como estudos de caso — todos
usando **software de microssimulação para redesenho de interseção**, não sistemas preditivos de
IA em operação contínua).

**Leitura para a entrevista:** há uma distância real entre (a) o que a literatura acadêmica
propõe como "sinalização preditiva" (ML sobre dado em tempo real) e (b) o que aparece como
prática mais comum em órgãos de trânsito (simulação de cenário pontual antes de redesenhar uma
interseção, via Aimsun/Vissim/SUMO). Isso é uma distinção importante para não confundir na
pergunta Q3.1 — "digital twin"/previsão de ML é bem mais raro na prática do que simulação
pontual de engenharia.

**Confiança:** baixa — baseado em resumo gerado por ferramenta de busca sobre múltiplos artigos,
não em leitura direta do texto completo (o principal está em paywall). Precisa de confirmação
independente antes de virar claim.
