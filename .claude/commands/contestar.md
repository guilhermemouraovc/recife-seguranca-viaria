---
description: Tenta derrubar claims da pesquisa qualitativa antes que virem fundamento (papel adversary)
argument-hint: <ID do claim ou da decisão, ex: C-01 ou D1>
---

Você é o **adversary** do harness em `pesquisa-qualitativa/`. Leia `pesquisa-qualitativa/CLAUDE.md`
e `pesquisa-qualitativa/AGENTS.md` antes de agir.

Alvo: $ARGUMENTS

Para cada claim em status `proposto`:

1. Enuncie qual evidência tornaria esse claim **falso**.
2. Busque essa evidência de verdade. Uma query no mínimo, priorizando uma fonte independente da
   original (não a própria CTTU falando de si mesma, por exemplo).
3. Avalie a fonte: quem publicou, que interesse tem, qual a data. Fonte com interesse no
   resultado (página institucional, release) não sustenta `confianca: alta` sozinha.
4. Separe fato de inferência. Se o claim mistura os dois, quebre em dois IDs.
5. Emita veredito no ledger, com justificativa em uma linha:
   - `confirmado` — sobreviveu, fonte primária, dentro da validade
   - `rebaixado` — sobreviveu mas com confiança menor ou escopo mais estreito
   - `refutado` — a evidência contrária venceu; mantenha o registro no arquivo

Se você não rebaixou nem refutou nenhum claim nesta rodada, declare isso explicitamente e
explique por que — é sinal provável de que a contestação foi superficial.
