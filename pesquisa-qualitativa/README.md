# pesquisa-qualitativa

Harness de pesquisa que fundamenta o roteiro de entrevista com profissionais da Secretaria de
Trânsito / CTTU (semana 3–4, ver `../docs/00-contexto-cesar.md`). Aqui não se decide solução —
isso é ideação, semana 5.

Adaptado do harness usado em outro projeto (papéis scout/synthesizer/adversary/architect +
ledger de claims contestáveis) para reaproveitar a mesma disciplina: nenhuma pergunta do
roteiro entra sem fonte, e toda afirmação é testada antes de virar fundamento.

## Como usar (sem precisar entender o resto deste arquivo)

1. Abra este repositório com Claude Code.
2. Escolha uma pergunta em `research/00-questions.md` (ex.: `Q1.2`) e peça pro agente
   `/pesquisar Q1.2` — ele levanta fontes e cria notas em `research/sources/`.
3. Depois de ter fontes suficientes pra uma decisão inteira (D1, D2 ou D3), peça
   `/consolidar D1` — ele transforma as fontes em claims no ledger (`research/claims.md`).
4. Peça `/contestar D1` — ele tenta derrubar cada claim antes de vira fundamento. Isso é o que
   evita perguntar pra Secretaria de Trânsito algo baseado em suposição errada.
5. Quando as 3 decisões (D1, D2, D3) tiverem claims contestados, peça `/fundamentar` — ele gera
   o roteiro de entrevista final e o mapeamento de quem responder cada pergunta em
   `artifacts/`.

Não precisa rodar na ordem perfeita nem esperar terminar tudo de uma decisão — dá pra ir e
voltar entre `/pesquisar` e `/consolidar` conforme aparecem novas perguntas.

## Fluxo

```
research/00-questions.md  ->  /pesquisar Q<n>   ->  research/sources/
research/sources/         ->  /consolidar D<n>  ->  research/claims.md + findings/
research/claims.md        ->  /contestar D<n>   ->  veredito no ledger
                               evals/ledger.eval.md  (portão)
claims confirmados        ->  /fundamentar      ->  artifacts/
```

`artifacts/` é a entrega: o roteiro de entrevista fundamentado, o mapeamento de quem responde
cada pergunta, e o brief para a ideação da semana 5.

## Decisões (ordem sugerida)

D1 (previsão vs. reação) e D2 (quem responde o quê) primeiro — sem elas não dá pra aplicar a
entrevista. D3 (apetite por camada aberta / "digital twin") é semente pra semana 5, mas ajuda a
formular uma pergunta melhor já na semana 4.

## Estrutura

```
CLAUDE.md                       contrato: o que vale como evidência neste harness
AGENTS.md                       quatro papéis e o que cada um não pode fazer
research/00-questions.md        perguntas de decisão (D1–D3)
research/claims.md              ledger — fonte única de verdade, já semeado com docs/06 e docs/08
research/sources/               notas cruas, uma por fonte
research/findings/               síntese por decisão
artifacts/                      roteiro de entrevista, mapeamento, brief pra ideação
evals/ledger.eval.md            portão de qualidade antes de /fundamentar
```

Comandos (`/pesquisar`, `/consolidar`, `/contestar`, `/fundamentar`) ficam em
`../.claude/commands/`, compartilhados com o resto do repo.

## Integração com o que já existe

- O ledger (`research/claims.md`) já nasce com claims extraídos de
  `../docs/08-fundamentacao-e-oportunidades.md` e `../docs/06-limitacoes-metodologicas.md` —
  eles entram como `proposto` (ainda não passaram pela contestação deste harness), exceto
  `C-02`, que já nasce `rebaixado` porque `docs/08` já registrou que a fonte original não o
  sustenta.
- Ressalvas metodológicas do PSVR/CTTU (`../docs/06`) valem para qualquer claim que use dado já
  extraído no pipeline principal deste repo.
- Contexto de prazo e do que ainda não pode ser tratado como decidido (ideação) está em
  `../docs/00-contexto-cesar.md`.
- `Q1.1` já rodou `/pesquisar` uma vez — `research/sources/` tem 4 notas de exemplo (páginas
  oficiais da CTTU + literatura internacional) mostrando o formato esperado.
