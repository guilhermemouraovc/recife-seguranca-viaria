# 03 — Ontologia do domínio

Objetivo: dar a um agente de código um modelo conceitual de como as entidades presentes nos
datasets catalogados se relacionam — e, principalmente, **onde essas relações não podem ser
inferidas diretamente**, para evitar joins inválidos.

## Entidades principais

**Sinistro/Chamado de trânsito** — evento pontual, com protocolo, data, hora, endereço,
natureza (com/sem vítima), tipo (colisão, atropelamento, capotamento etc.). Fonte:
dataset consolidado da CTTU (seção A do catálogo).

**Vítima** — pessoa envolvida em um sinistro. No dataset da CTTU, vítimas **não são linhas
próprias**: o CSV traz contadores agregados por sinistro (`vitimas`, `vitimasfatais`) e
contadores por tipo de envolvido (`auto`, `moto`, `ciclista`, `pedestre`, `onibus`,
`caminhao`...), não um registro individual por vítima com idade/sexo. Já o dataset do SAMU
traz `sexo` e `idade` por chamado — mas é chamado de saúde, não sinistro de trânsito
tipificado (ver adiante).

**Veículo envolvido** — inferido indiretamente no dataset de sinistros pelas colunas de
contagem por tipo (não há um registro de veículo com placa/marca/modelo).

**Local** — via, bairro, endereço, cruzamento, e nos datasets de equipamentos/semáforos,
coordenadas (latitude/longitude). O dataset de sinistros só tem endereço textual, sem
lat/long — geocodificação seria necessária para juntar espacialmente com equipamentos ou
semáforos.

**Equipamento de fiscalização** (radar, lombada eletrônica, fotossensor) — tem
identificação, local de instalação, lat/long, velocidade regulamentada e VMD (volume médio
diário). Gera dois tipos de dado derivado: registros de **velocidade** (contagem de veículos
por faixa de velocidade, por equipamento) e **infrações** (multas por excesso de velocidade
ou outras).

**Infração/multa** — evento de fiscalização, com data/hora, tipo de infração, base legal e
local (texto), **não geolocalizado diretamente** — teria que ser casado com o cadastro de
equipamentos pelo campo `agenteequipamento`/local, quando aplicável (nem toda infração vem
de equipamento fixo — pode ser blitz, fiscalização humana etc.).

**Semáforo** — infraestrutura de via, com lat/long e atributos (equipado para ciclistas,
para deficientes visuais). Não tem relação direta codificada com sinistros — só espacial
(por proximidade geográfica).

**Atendimento SAMU** — chamado de emergência de saúde, com data/hora, bairro, endereço,
origem do chamado, `tipo`/`subtipo` (ex.: "CAUSAS EXTERNAS" / "ACIDENTE DE TRANSITO
ENVOLVENDO MOTO"), sexo, idade e desfecho. É o dataset mais próximo de dar uma dimensão de
"vítima individual", mas cobre toda a Região Metropolitana, não é filtrado por trânsito por
padrão (precisa filtrar por `tipo`/`subtipo`), e não tem qualquer campo que aponte para um
`Protocolo` de sinistro da CTTU.

**Indicador/meta do PSVR** — não vem em dataset tabular; está descrito em texto/tabelas
dentro do PDF do PSVR (eixos, iniciativas, ações, indicadores, metas 2026–2036). Tratar como
fonte qualitativa/semiestruturada a ser extraída do PDF, não como uma tabela relacional.

## Relações entre entidades

- Sinistro **ocorre em** um Local (texto livre — bairro, endereço, cruzamento).
- Sinistro **envolve** Veículo(s) (via colunas de contagem por tipo, não registros
  individuais).
- Sinistro **pode ter** Vítima(s) (contagem agregada, não fatos individuais).
- Local **pode ter** Equipamento de fiscalização (relação espacial, via lat/long — precisa
  geocodificar o endereço do sinistro para aproximar).
- Equipamento **gera** registros de Velocidade (uma linha por faixa de 15 min por faixa de
  velocidade).
- Equipamento **pode gerar** Infração (quando a infração é automática, por excesso de
  velocidade).
- Atendimento SAMU **pode corresponder** a um Sinistro da CTTU quando `subtipo` menciona
  trânsito — mas essa é uma correspondência **probabilística por data + hora + bairro
  aproximados**, nunca uma chave exata. Trate qualquer join SAMU↔CTTU como uma hipótese a
  validar, não como um fato.

## O que NÃO existe (e não deve ser assumido)

- **Não há chave única compartilhada** entre nenhum par de datasets (nenhum `protocolo`,
  `id_sinistro` ou equivalente aparece em mais de uma fonte).
- **Não há geolocalização no dataset de sinistros** — só texto livre de endereço. Qualquer
  join espacial com equipamentos/semáforos exige geocodificação prévia (e validação manual
  de uma amostra, dado o histórico de erros de digitação de endereço observado nos CSVs).
- **Os números dos relatórios institucionais (PSVR, Relatórios Anuais) não reconciliam
  automaticamente com os datasets abertos** — são produzidos por processos estatísticos
  diferentes (ver `06-limitacoes-metodologicas.md`). Não trate a soma de um CSV como
  "a mesma coisa" que o número citado num relatório, mesmo quando parecerem próximos.
