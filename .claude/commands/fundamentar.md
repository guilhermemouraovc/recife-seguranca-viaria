---
description: Gera o roteiro de entrevista e artefatos da pesquisa qualitativa (papel architect)
---

Você é o **architect** do harness em `pesquisa-qualitativa/`. Leia `pesquisa-qualitativa/CLAUDE.md`
e `pesquisa-qualitativa/AGENTS.md` antes de agir.

Pré-condição: rode `pesquisa-qualitativa/evals/ledger.eval.md` primeiro. Se o ledger reprovar em
E1, E2 ou E7, pare e reporte — não gere artefato sobre base podre.

Produza, nesta ordem, dentro de `pesquisa-qualitativa/artifacts/`:

1. `1-roteiro-entrevista.md` — perguntas organizadas por decisão (D1, D2, D3), cada uma citando
   o `[C-nn]` que a motiva ou marcada explicitamente como "pergunta aberta, sem fundamentação
   prévia". Só claims `confirmado` sustentam uma pergunta como "fundamentada"; claims
   `proposto`/`rebaixado` viram pergunta explícita de verificação, não afirmação.
2. `2-mapeamento-respondentes.md` — para cada pergunta, o perfil/cargo dentro da Secretaria de
   Trânsito/CTTU que deveria respondê-la (engenharia viária, fiscalização, gestão de dados),
   com base nos claims de D2. Onde a estrutura organizacional não estiver clara, escreva
   `EM ABERTO — perguntar na primeira entrevista`, não invente organograma.
3. `3-brief-para-ideacao.md` — o que ficou confirmado, o que ficou em aberto, riscos (ex.:
   confundir camada analítica com "digital twin" preditivo, ver `C-04`) e o que precisa ser
   resolvido antes da semana 5. Sem propor solução — decisão de produto é humana.

Regra de forma: toda afirmação sobre o mundo carrega `[C-nn]`. Nenhuma pergunta do roteiro
pressupõe uma solução já escolhida.
