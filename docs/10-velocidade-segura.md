# 10 — Velocidade segura: parâmetro de referência

Registro do que o projeto usa como "velocidade segura" e do que **não** está definido. Três
coisas diferentes que não devem ser misturadas em gráfico, score ou texto:

| Conceito | O que é | Fonte |
|---|---|---|
| **Velocidade segura** | Velocidade de impacto que o corpo humano sobrevive, por tipo de conflito | OMS (Sistema Seguro) |
| **Limite legal padrão** | Máximo permitido onde **não há placa** | CTB, art. 61 §1º |
| **Limite municipal** | Máximo que o Recife fixou para suas vias | Plano de Mobilidade Urbana (a confirmar) |

## 1. Velocidade segura (parâmetro adotado pelo projeto)

OMS et al., *Speed management: a road safety manual for decision-makers and practitioners*,
2ª ed., 2023, Tabela 1, p. 4
([PDF](https://cdn.who.int/media/docs/default-source/documents/health-topics/road-traffic-injuries/3146-wbk-speed-mgmt-2nd-edition-131023-electronic.pdf),
acessado 22/10/2026):

| Tipo de via / trecho | Velocidade segura |
|---|---|
| Possível conflito entre carro e usuário vulnerável (pedestre, ciclista) | máx. **30 km/h** |
| Interseções com possível colisão lateral entre carros | máx. **50 km/h** |
| Possível colisão frontal entre carros | máx. **70 km/h** |
| Sem possibilidade de colisão lateral nem frontal | máx. **100 km/h** |

O mesmo texto (p. 3) diz que motociclistas, como usuários sem proteção, têm limiar parecido
com o de pedestres e ciclistas (~30 km/h). Isso pesa no Recife: a moto está envolvida em ~35% dos
sinistros da base 2015–2024 e em 76% dos de 2024 (`data/processed/sinistros/README.md`; lembrar
que a cobertura da base muda muito a partir de 2020).

**Correção de `docs/08`:** a frase "velocidade considerada segura pela OMS (30–50 km/h)" vem
de matéria de jornal. A fonte primária é a tabela acima, com valor **por tipo de conflito**,
não uma faixa única.

## 2. Limite legal padrão (CTB, art. 61 §1º)

Só vale **onde não existe sinalização regulamentadora**
([Lei 9.503/1997](https://www.planalto.gov.br/ccivil_03/leis/l9503compilado.htm), acessado
22/10/2026). Em vias urbanas: 80 km/h nas de trânsito rápido, 60 km/h nas arteriais, 40 km/h nas
coletoras e 30 km/h nas locais. O órgão de trânsito pode sinalizar outro valor. Ou seja, o CTB
não fixa um teto; o limite real é o da placa.

## 3. Limite municipal do Recife (a confirmar)

Matérias de 07/2026 (Diário de Pernambuco, Folha PE) dizem que a lei municipal da Política e
Plano de Mobilidade Urbana do Recife, **art. 34**, fixa **50 km/h nas arteriais** e até
**60 km/h nas de trânsito rápido**. Isso foi usado para baixar a Av. Boa Viagem de 60 para
50 km/h. **Não confirmado na fonte primária:** o número da lei e o texto final do art. 34
não foram localizados, e uma emenda ao PL 42/2021 tratava o art. 34 como critério de
travessia de pedestre. Uma minuta de 2018 trazia 60/50/40/30 km/h (trânsito
rápido/arterial/coletora/local). Até alguém ler a lei, tratar como indício.

## 4. O que não está definido

- **PSVR 2026–2036, Iniciativa 4.3**, quer "adequar os limites de velocidade de acordo com
  parâmetros seguros", mas **não diz quais são** (nenhum valor em km/h no texto extraído).
  A ação prevista é justamente um estudo técnico, com piloto, sob responsabilidade da
  SEOPS-CTTU. O parâmetro é pergunta da entrevista (`pesquisa-qualitativa/`, Q1.6).
- **Classificação viária** (local/coletora/arterial) não está em nenhuma base baixada. Sem
  ela, não dá para comparar automaticamente o limite de cada via com a velocidade segura.

## 5. Como usar nos dados

- **Sinistros:** `velocidade_max_via` é o **limite sinalizado**, preenchido só em ~25% das
  linhas, de 2018 a 2022. Comparar com a tabela da seção 1 dá "limite acima do seguro", não
  "velocidade praticada".
- **Velocidade das vias** (contagem por faixa de 10 km/h por equipamento, ainda não baixada):
  dá para calcular "% de veículos acima de 30/50 km/h". As faixas `qtd_21a30km`/`qtd_41a50km`
  batem com os limiares.
- **Score de risco** (`sql/02_risco.sql`): **não usa velocidade** hoje.
