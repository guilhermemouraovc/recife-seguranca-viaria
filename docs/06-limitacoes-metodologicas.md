# 06 — Limitações metodológicas conhecidas

Estas ressalvas já foram identificadas (algumas vêm da própria ficha dos datasets, outras
foram observadas ao inspecionar os dados). Elas precisam **sobreviver** no pipeline de
código e em qualquer artefato de dados gerado — não corrigir ou esconder silenciosamente.

## 1. Cobertura parcial de 2015

O dataset consolidado de sinistros (`acidentes-de-transito-com-e-sem-vitimas`) só tem dados
de 2015 a partir de junho. Qualquer agregação anual que inclua 2015 subestima o ano
inteiro — sinalizar isso explicitamente em qualquer gráfico/tabela que use esse ano.

## 2. "Chamados" ≠ "registros estatísticos dos relatórios anuais"

O próprio portal declara que o dataset é de **chamados** de sinistro, e que pode divergir
dos números publicados nos Relatórios Anuais de Segurança Viária, que usam **registros
estatísticos produzidos pelos agentes de trânsito**. São dois processos de coleta
diferentes — não tratar como a mesma fonte de verdade, mesmo quando os números parecerem
compatíveis. Isso já foi incorporado no relatório de desk research entregue; o código
precisa preservar essa distinção (ex.: nunca rotular uma soma do CSV como "número oficial
do PSVR" sem essa ressalva ao lado).

## 3. Dados de 2025 são preliminares

O PSVR usa 2025 como ano-base, mas o próprio programa classifica esses números como
preliminares. Se o pipeline processar dados de 2025 (de qualquer fonte), rotular como tal.

## 4. URLs de recurso são assinadas e expiram (~1h)

Ver `05-arquitetura-extracao.md`. Isso não é uma limitação dos dados em si, mas uma
limitação operacional que, se ignorada, quebra qualquer manifesto que tente cachear a URL
final de download.

## 5. Corrupção de encoding na fonte (dataset de Equipamentos)

Confirmado inspecionando os bytes brutos do CSV `lista-de-equipamentos-de-fiscalizacao-de-
transito.csv`: o texto `"AV. ENG. JOS\x90 ESTELITA, APàS PTE. AGAMENON MAGALHAES"` contém um
byte `0x90` inválido tanto em UTF-8 quanto em Latin-1/CP1252 puro, e o `"à"` no lugar de
`"Ó"` sugere um problema de encoding que já existia na base de origem da CTTU (não é um
artefato do download). Decisão a tomar no pipeline: (a) decodificar com `errors="replace"` e
sinalizar as linhas afetadas, ou (b) manter os bytes brutos e documentar que endereços com
caracteres estranhos precisam de revisão manual antes de qualquer geocodificação. Não
"adivinhar" a correção do texto sem validação humana.

## 6. Ausência de chave de junção entre bases

Nenhum dataset catalogado compartilha um identificador único com outro (ver
`03-ontologia.md`). Qualquer cruzamento (ex.: sinistros × SAMU, sinistros × equipamentos de
fiscalização) é uma correspondência aproximada por data/hora/local, sujeita a falsos
positivos e negativos. Resultados de joins devem vir acompanhados da metodologia de
correspondência usada e de uma estimativa de incerteza, não apresentados como fatos exatos.

## 7. Ausência de geolocalização nos sinistros

O dataset de sinistros só tem endereço em texto livre (sem lat/long), diferente dos
datasets de equipamentos e semáforos (que têm lat/long). Qualquer análise espacial exige
geocodificação prévia do endereço — processo sujeito a erro, especialmente dado que os
próprios endereços têm inconsistências de digitação (abreviações, falta de acentuação,
referências relativas como "em frente ao..." ou "após..." em vez de endereço exato).

## 8. SAMU cobre a Região Metropolitana, não só o Recife

Se não for filtrado por `municipio == "RECIFE"`, qualquer contagem do dataset do SAMU vai
inflar os números em relação ao que é citado nos relatórios do Recife.

## 9. Campos sistematicamente vazios podem refletir mudança de formulário, não falta de dado real

Várias colunas de contexto do dataset de sinistros (clima, situação do semáforo,
sinalização, condição da via etc.) vieram vazias na amostra de 2024 inspecionada. Antes de
tratar como "dado ausente" de forma genérica, verificar se essas colunas são preenchidas em
outros anos — pode indicar que o formulário de coleta mudou ao longo do tempo, o que é em
si um achado relevante para o relatório (limitação da série histórica), não só um problema
técnico a contornar.
