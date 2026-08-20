# Eval — integridade do claim ledger

Portão entre pesquisa e artefato. Roda antes de `/fundamentar`.
Reprovou, não gera artefato.

## Como rodar

Leia `research/claims.md`, `research/sources/` e `research/00-questions.md`. Avalie cada
critério, dê PASSA/FALHA e liste os IDs infratores.

---

### E1 — Rastreabilidade

Todo claim tem `fonte` com URL e data de acesso, ou, se `tipo: lacuna`, tem as queries literais
(ou a referência ao doc que já tentou e falhou, como `C-02`) registradas.
**Falha se:** qualquer claim tem fonte vazia, genérica ("pesquisa na internet") ou sem data.

### E2 — Fato não contaminado por desejo

Nenhum claim `tipo: fato` contém inferência, projeção ou opinião de solução.
**Falha se:** um claim afirma o que a Secretaria *vai* fazer, o que a entrevista *vai* revelar,
ou pressupõe uma solução (violaria também a regra 8 do `CLAUDE.md`).

### E3 — Confiança calibrada

`confianca: alta` só com fonte primária verificada nos últimos 12 meses.
**Falha se:** claim `alta` apoiado em fonte secundária, em página institucional sem confirmação
por terceiro, ou em dado sem data.

### E4 — Contestação real

Todo claim `confirmado` tem campo `contestacao` preenchido com o que foi tentado, não com "ok"
ou "verificado".
**Falha se:** a rodada de contestação não rebaixou nem refutou nada e não justificou por quê.

### E5 — Cobertura internacional onde há literatura relevante

Toda decisão cujo tema tem literatura ou benchmark internacional relevante (predição/simulação
de tráfego, "digital twin", Vision Zero) tem pelo menos uma fonte em inglês, além das fontes em
português sobre o contexto local de Recife.
**Falha se:** uma decisão com claim sobre benchmark internacional (ex.: D3) está fundamentada só
em fonte em português.

### E6 — Antecedência da lacuna

Toda pergunta em `00-questions.md` com status `respondida` tem pelo menos um claim apontando
para ela.
**Falha se:** pergunta marcada como respondida sem claim correspondente.

### E7 — Sem órfão no artefato

(Só quando `artifacts/` já existe.) Toda afirmação factual nos artefatos tem `[C-nn]` e o ID
existe no ledger com status `confirmado`.
**Falha se:** artefato cita claim `proposto`, `rebaixado` ou inexistente.

---

## Veredito

- **7/7** — pode gerar artefato.
- **E1, E2 ou E7 falhando** — bloqueio duro, corrige antes de qualquer coisa.
- **demais falhando** — gera artefato marcando explicitamente a fragilidade no topo de
  `3-brief-para-ideacao.md`.
