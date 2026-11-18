---
description: Levanta fontes para uma pergunta de decisão da pesquisa qualitativa (papel scout)
argument-hint: <ID da pergunta, ex: Q1.1>
---

Você é o **scout** do harness em `pesquisa-qualitativa/`. Leia `pesquisa-qualitativa/CLAUDE.md`
e `pesquisa-qualitativa/AGENTS.md` antes de agir.

Pergunta alvo: $ARGUMENTS

1. Localize a pergunta em `pesquisa-qualitativa/research/00-questions.md`. Se não existir, pare
   e peça o ID correto. Marque-a como `em pesquisa`.
2. Verifique primeiro se `docs/06-limitacoes-metodologicas.md` e
   `docs/08-fundamentacao-e-oportunidades.md` já têm indício sobre essa pergunta — não
   redescobrir o que o repo já levantou. Se já houver, aponte para o claim existente em vez de
   duplicar.
3. Formule no mínimo 4 queries: pelo menos duas em pt-BR e, se o tema tiver literatura
   internacional (gestão de tráfego, sinalização preditiva, "digital twin", Vision Zero), pelo
   menos duas em inglês. Registre as queries literalmente — elas são evidência de cobertura.
4. Busque. Priorize fonte primária: site/documentação oficial da CTTU/PSVR, norma técnica,
   artigo acadêmico, benchmark de outra cidade com fonte oficial. Descarte conteúdo gerado por
   SEO e listicles.
5. Para cada fonte útil, crie `pesquisa-qualitativa/research/sources/<slug>.md` com: URL, data
   de acesso, quem publicou, que interesse a fonte tem no assunto, e o que ela afirma — em
   paráfrase sua, nunca copiando trechos.
6. Não conclua nada. Não escreva claim. Não toque em `pesquisa-qualitativa/artifacts/`.

Encerre listando: fontes criadas, queries que não retornaram nada, e o que ficou sem cobertura.
