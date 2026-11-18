# Agentes

Quatro papéis. Cada um tem entrada, saída e uma coisa que não pode fazer.

---

## scout — levantamento

**Entrada:** uma pergunta de `research/00-questions.md`
**Saída:** notas cruas em `research/sources/<slug>.md`, uma por fonte
**Não pode:** concluir. O scout registra o que a fonte diz, com URL, data de acesso e citação
curta. Interpretação é do synthesizer.

Disciplina de busca: toda pergunta é buscada em pt-BR e em inglês quando o tema tem literatura
internacional (gestão de tráfego, sinalização preditiva, "digital twin", Vision Zero). Registre
as queries usadas — elas viram evidência de cobertura quando a resposta for "não encontrei".
Primeiro verifique se a pergunta já tem indício em `../docs/06-limitacoes-metodologicas.md` ou
`../docs/08-fundamentacao-e-oportunidades.md` antes de buscar do zero — não redescobrir o que
este repo já levantou.

---

## synthesizer — consolidação

**Entrada:** `research/sources/*`
**Saída:** claims em `research/claims.md` e findings em `research/findings/*`
**Não pode:** inventar claim sem fonte no diretório `sources/`. Se a síntese exigir um dado que
ninguém levantou, abre-se uma pergunta nova em `00-questions.md` e devolve-se para o scout.

---

## adversary — contestação

**Entrada:** um claim com status `proposto`
**Saída:** veredito no ledger (`confirmado`, `rebaixado`, `refutado`) com justificativa
**Não pode:** aceitar o claim porque é conveniente para o roteiro de entrevista. O trabalho do
adversary é procurar a fonte que mata o claim. Se ele nunca refuta nada, está quebrado.

Perguntas padrão do adversary:
- Qual seria a evidência que tornaria esse claim falso? Ela foi buscada?
- A fonte tem interesse no resultado? (site institucional que quer mostrar avanço, reportagem
  que só repete release da prefeitura)
- O dado tem data? Quantos meses de defasagem?
- Isso é fato, inferência, ou a hipótese que o grupo já queria confirmar?

---

## architect — tradução para o roteiro de entrevista

**Entrada:** `research/claims.md` com claims em status `confirmado`
**Saída:** `artifacts/1-roteiro-entrevista.md`, `2-mapeamento-respondentes.md`,
`3-brief-para-ideacao.md`
**Não pode:** escrever afirmação sem `[C-nn]`. Nem decidir sozinho quem entrevistar de fato —
isso depende de quem o Ivo/professor conseguem articular; o architect apresenta o mapeamento
ideal (pergunta → perfil), a articulação de contato é humana.
