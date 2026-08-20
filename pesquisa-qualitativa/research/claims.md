# Claim ledger

Registro único de tudo que este harness afirma saber. Artefato que cita fato cita daqui.

## Formato

```
### C-nn — <afirmação em uma linha>
tipo:       fato | estimativa | lacuna
confianca:  alta | media | baixa
status:     proposto | confirmado | rebaixado | refutado
fonte:      <URL + data de acesso>  (ou: queries rodadas, se tipo=lacuna)
evidencia:  <o que exatamente a fonte diz — paráfrase, não cópia>
decisao:    <qual pergunta de 00-questions este claim serve>
contestacao: <o que o adversary tentou e o que sobrou>
```

Regras:
- ID nunca é reciclado. Claim refutado fica no arquivo com status `refutado`.
- Claim que muda de conteúdo vira ID novo, com `substitui: C-nn`.
- `confianca` sem data de acesso é inválida.

---

## Seed — claims herdados de `../../docs/06` e `../../docs/08`

Estes já tinham fonte citada no desk research, mas entram como `proposto` porque ainda não
passaram pela contestação deste harness — exceto `C-02`, que `docs/08` já verificou e a fonte
não sustentou.

### C-01 — Recife (CTTU) tem um eixo formal de "Gestão de Dados" dentro do PSVR
tipo: fato
confianca: media
status: proposto
fonte: CTTU — Gestão de dados do Recife, https://cttu.recife.pe.gov.br/gestao-de-dados-do-recife — acessado 18/08/2026 (via `../../docs/08-fundamentacao-e-oportunidades.md`, seção 4)
evidencia: página institucional descreve um eixo de gestão de dados que alimenta continuamente os eixos de fiscalização, engenharia viária e educação/comunicação do PSVR
decisao: D1 (Q1.2) — ponto de partida para perguntar se esse eixo já faz algo preditivo ou só consolida indicadores
contestacao: pendente — página é a própria CTTU falando de si mesma, sem terceiro confirmando o que o eixo produz na prática

### C-02 — A existência de um comitê "Compat" (CTTU + SAMU + Defesa Social) que reconcilia dados de sinistro
tipo: lacuna
confianca: baixa
status: rebaixado
fonte: tentativa de verificação registrada em `../../docs/08-fundamentacao-e-oportunidades.md`, seção 4 (checagem em 08/2026) — a matéria da CBN Recife originalmente citada é de 08/03/2022, sobre o relatório 2017–2020, e não menciona "Compat" nem SAMU/Defesa Social; a página oficial do PSVR também estava inacessível na tentativa de confirmação
evidencia: a afirmação nasceu de conversa, não de fonte direta, e não sobreviveu à checagem
decisao: D2 (Q2.1) — não perguntar "como funciona o Compat" (pressupõe que existe); perguntar se existe algo equivalente, sem nomear
contestacao: já contestado em `docs/08` — fonte não sustenta o claim; mantido como lacuna, não deletado

### C-03 — CTTU mede velocidade das vias desde 2020, em parceria com BIGRS/Johns Hopkins University/UFC
tipo: fato
confianca: media
status: proposto
fonte: Folha PE, https://www.folhape.com.br/noticias/cttu-inicia-pesquisa-de-monitoramento-da-velocidade-media-e-o/446566/ — acessado 18/08/2026 (via `../../docs/08`, seção 3)
evidencia: reportagem descreve o início da pesquisa de monitoramento de velocidade média pela CTTU, com participação de BIGRS/Johns Hopkins/UFC; dado usado hoje mostra 43% das motos e 75% dos veículos em geral acima da velocidade segura (OMS)
decisao: D1 (Q1.3) — mostra capacidade de instrumentação contínua; pergunta em aberto é se isso já é insumo de decisão ou só relatório
contestacao: pendente — confirmar se a métrica de velocidade influencia diretamente alguma decisão de engenharia viária, ou se fica isolada como indicador de acompanhamento

### C-04 — Cidades com programas Vision Zero data-driven publicam camadas analíticas derivadas do dado bruto (não simulação preditiva)
tipo: fato
confianca: media
status: proposto
fonte: the-atlas.com (SANDAG Safety Focus Network) — acessado 18/08/2026; blogs.microsoft.com/newyork (NYC Crash & Interventions Map) — acessado 18/08/2026 (ambos via `../../docs/08`, seção 5)
evidencia: SANDAG identifica que 6% da malha viária concentra 54% dos sinistros graves/fatais; NYC cruza sinistro com intervenção de engenharia já realizada. Nenhum dos dois é um "digital twin" de simulação preditiva — são camadas analíticas retrospectivas sobre dado histórico
decisao: D3 (Q3.2) — benchmark pra perguntar se uma camada assim (não necessariamente simulação) já resolveria algo pra quem decide hoje
contestacao: pendente — risco de a entrevista confundir "camada analítica retrospectiva" com "simulação preditiva/digital twin"; são conceitos diferentes, não misturar nas perguntas (ver nota em Q3.1 vs Q3.2)
