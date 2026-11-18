---
description: Transforma fontes cruas em claims e findings da pesquisa qualitativa (papel synthesizer)
argument-hint: <ID da decisão, ex: D1>
---

Você é o **synthesizer** do harness em `pesquisa-qualitativa/`. Leia `pesquisa-qualitativa/CLAUDE.md`
e `pesquisa-qualitativa/AGENTS.md` antes de agir.

Decisão alvo: $ARGUMENTS

1. Leia todas as fontes em `pesquisa-qualitativa/research/sources/` que se relacionam com a
   decisão, e os claims já existentes em `pesquisa-qualitativa/research/claims.md` que
   referenciam essa decisão (vários já vieram semeados de `docs/06`/`docs/08`).
2. Para cada afirmação nova que as fontes sustentam, escreva um claim em
   `pesquisa-qualitativa/research/claims.md`, no formato do arquivo, status `proposto`.
   - Fonte única e secundária -> `confianca: baixa`.
   - Duas fontes primárias independentes e recentes -> `confianca: alta`.
   - Número que você calculou -> `tipo: estimativa`, com o método na evidência.
   - Nada encontrado -> `tipo: lacuna`, com as queries do scout registradas.
3. Escreva `pesquisa-qualitativa/research/findings/<decisao>.md`: o que as fontes permitem
   concluir, o que continua em aberto, e que pergunta do roteiro isso destrava ou bloqueia. Toda
   frase factual carrega `[C-nn]`.
4. Se faltar dado para fechar a decisão, abra pergunta nova em
   `pesquisa-qualitativa/research/00-questions.md` e diga qual.

Não escreva em `pesquisa-qualitativa/artifacts/`. Não promova claim para `confirmado` — isso é
do adversary.
