# Contrato — harness de pesquisa qualitativa (segurança viária, Recife)

## Propósito

Fundamentar o roteiro de entrevista com profissionais da Secretaria de Trânsito / CTTU
(semana 3–4 do cronograma, ver `../docs/00-contexto-cesar.md`) antes de ele ser aplicado.
Nenhuma pergunta do roteiro entra sem uma razão rastreável — ou um claim que a motiva, ou uma
lacuna explícita que a entrevista precisa fechar. A saída deste harness é insumo para a
entrevista e, depois, para a ideação da semana 5 — não é a ideação em si.

## Definição de pronto

Este harness está pronto quando existirem:

- `artifacts/1-roteiro-entrevista.md` — toda pergunta rastreia para um `[C-nn]` do ledger, ou
  está marcada explicitamente como pergunta aberta (sem fundamentação prévia disponível).
- `artifacts/2-mapeamento-respondentes.md` — cada pergunta ligada a um perfil/cargo dentro da
  Secretaria de Trânsito, CTTU ou órgão correlato.
- `artifacts/3-brief-para-ideacao.md` — o que ficou decidido, o que ficou em aberto, e riscos
  identificados para levar à semana 5.

## Regras invioláveis

1. **Sem claim, sem afirmação.** Qualquer frase nos `artifacts/` que afirme algo sobre o mundo
   (o que a Secretaria faz, o que já existe em outra cidade, o que a literatura diz) carrega um
   ID `[C-nn]`. Frase sem ID é opinião e volta.
2. **Fonte primária ou nada.** Para este domínio, fonte primária é: documentação/site oficial da
   CTTU ou PSVR, norma técnica (CONTRAN, DENATRAN, ABNT), artigo acadêmico com revisão por
   pares, dado já extraído neste repo (`../docs/`, `../data/`), benchmark de outra cidade com
   fonte oficial, ou a transcrição de uma entrevista já realizada. Notícia que cita fonte
   primária identificável entra como `confianca: media`; notícia sem fonte rastreável ou blog
   de terceiro entra como `confianca: baixa` e precisa de confirmação independente para subir.
3. **Confiança é declarada, não implícita.** `alta` = fonte primária verificada nos últimos 12
   meses. `media` = fonte primária desatualizada, ou secundária que cita fonte primária
   identificável. `baixa` = indício único, não confirmado.
4. **Estimativa é marcada como estimativa.** Número calculado, inferido ou chutado entra como
   `tipo: estimativa`, com o método explícito ao lado. Nunca vira `fato` por repetição.
5. **Ausência de evidência não é evidência.** "Não encontrei confirmação de X" é um claim sobre
   a busca, não sobre a Secretaria. Registra-se como `C-nn tipo: lacuna` com as queries
   rodadas — e vira pergunta explícita no roteiro, não afirmação disfarçada.
6. **Todo claim que sustenta uma pergunta do roteiro passa por contestação.** Antes de virar
   artefato, o claim é submetido a `/contestar`. Claim que não sobrevive é rebaixado, não
   deletado — o registro do erro é útil (ex.: `C-02` neste ledger).
7. **Decisão antes de pesquisa.** Só se pesquisa o que destrava uma decisão listada em
   `research/00-questions.md`. Curiosidade sem decisão associada não entra no escopo.
8. **Ideação continua fora de escopo.** A entrevista é levantamento, não validação de solução —
   ideação só começa na semana 5 (ver `../docs/00-contexto-cesar.md`). Não formular pergunta
   que pressuponha uma solução já escolhida (ex.: perguntar "o que acham do nosso dashboard"
   antes de existir um dashboard).
9. **Ressalvas metodológicas já conhecidas não se perdem.** Qualquer claim que use dado do PSVR/
   CTTU já extraído neste repo carrega as ressalvas de `../docs/06-limitacoes-metodologicas.md`
   (cobertura parcial de 2015, "chamados" ≠ relatório anual, 2025 preliminar) quando relevante.

## Antipadrões que invalidam o trabalho

- Perguntar só o que confirma a hipótese de que "falta dado" — a hipótese concorrente (dado
  existe, mas o processo de uso é manual/informal) já tem indício em `../docs/08`, item 4.
- Assumir que uma afirmação levantada em pesquisa anterior (`../docs/08`) já está confirmada
  só porque está documentada — ela entra neste ledger como `proposto`, igual a qualquer claim
  novo, a menos que já tenha passado por contestação (ver `C-02`, rebaixado).
- Consolidar antes de contestar.
- Escrever o roteiro com perguntas que pressupõem resposta (pergunta fechada travestida de
  aberta).
