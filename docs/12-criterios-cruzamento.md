# 12 — Critérios de cruzamento entre as bases

Como (e até onde) dá para ligar um sinistro da CTTU ao atendimento de saúde (SAMU) e ao
registro policial (SDS — Secretaria de Defesa Social de PE). Complementa
`03-ontologia.md` (relações entre entidades) e `06-limitacoes-metodologicas.md` #6 (não há
chave de junção). É a especificação da tarefa T8 de `07-backlog-tarefas.md`.

## 1. Escopo do MVP: só dados públicos

O MVP usa **apenas dados abertos**:

| Base | Situação | Entra no MVP? |
|---|---|---|
| Sinistros CTTU 2015–2024 (`data/processed/sinistros/`) | Aberta (CKAN, ODbL) | Sim |
| SAMU — "Solicitações de Atendimento" por ano | Aberta (CKAN), um registro por chamado, sem identificação pessoal | Sim, só como cruzamento **aproximado** e agregado |
| SAMU — microdados de atendimento (ficha, horário de chegada, condição da vítima, destino hospitalar) | Restrita | **Não** — depende de convênio com a Secretaria de Saúde |
| SDS — boletins de ocorrência / registros de óbito | Restrita | **Não** — depende de convênio com a SDS |

Tudo o que está nas seções 4 e 5 abaixo sobre SAMU-microdados e SDS é **desenho para depois
do convênio**, não algo que o MVP entrega. Nenhum resultado do MVP deve ser apresentado como
se tivesse usado essas bases.

Mesmo a base aberta do SAMU traz sexo, idade e bairro por chamado: usar só de forma
agregada e **nunca** tentar reidentificar pessoas (ver `CLAUDE.md`).

## 2. Campos em comum

Nenhum campo é uma chave. Estes são os que permitem **aproximar** registros:

| Dimensão | Sinistros CTTU | SAMU (aberto) | SDS (convênio, a confirmar) | Qualidade para cruzar |
|---|---|---|---|---|
| **Data** | `data` | `data` | data do fato | Boa — mas um sinistro perto da meia-noite pode virar chamado no dia seguinte |
| **Hora** | `hora` (`HH:MM:SS`; ~2.700 vazias ou inválidas) | `hora_minuto` | hora do fato / do registro | Média — é a hora do *chamado*, não a do sinistro, nas duas bases |
| **Município** | implícito (só Recife) | `municipio` (Região Metropolitana inteira) | município | Filtro obrigatório: `municipio == "RECIFE"` no SAMU |
| **Bairro** | `bairro` (normalizado) | `bairro` | bairro | Média — grafias diferentes e erros de digitação; normalizar igual nas duas pontas |
| **Endereço** | `endereco` + `numero` + `complemento` (texto livre); lat/lon por rua+bairro em `sinistros_2015_2024_geo.parquet` | `endereco` (texto livre) | logradouro | Fraca — referências relativas ("E/F AO...", "APÓS..."); só serve como desempate |
| **Tipo de vítima** | `usuario_vulneravel`, `envolve_pedestre/ciclista/moto` (participantes envolvidos, **não** vítimas) | `subtipo` (ex.: `ACIDENTE DE TRANSITO ENVOLVENDO MOTO`) | condição da vítima (condutor/passageiro/pedestre) | Média — categorias diferentes; comparar só em nível grosso (moto / pedestre / ciclista / outro) |
| **Gravidade** | `gravidade`, `vitimas`, `vitimasfatais` | `motivo_desfecho`, `motivo_finalizacao` | lesão / óbito | Serve como filtro de compatibilidade (ver 3.1) |
| **Pessoa** | — | `sexo`, `idade` (sem nome) | nome, documento, nascimento | Só SDS × SAMU-microdados teriam identificação pessoal — fora do MVP |

Os valores possíveis de `subtipo`, `motivo_desfecho` e `motivo_finalizacao` do SAMU ainda
**não foram levantados**. Fazer isso pelo dicionário oficial de cada ano (T5) antes de
fixar qualquer filtro.

## 3. Correspondência probabilística (record linkage)

Modelo Fellegi–Sunter: cada par candidato (sinistro, atendimento) recebe um peso somando a
evidência de cada campo; pares acima de um limiar viram "provável mesmo evento". Etapas:

### 3.1 Pré-filtros (antes de comparar)

- **SAMU:** `municipio == "RECIFE"` e `subtipo` de trânsito.
- **Sinistros:** só `gravidade` em `COM VÍTIMA` / `VÍTIMA FATAL`. Um sinistro `SEM VÍTIMA`
  não deveria gerar atendimento SAMU; se aparecer par forte com ele, é sinal de erro de
  classificação, a ser reportado, não descartado em silêncio.
- **Sinistros:** decidir e documentar se `situacao` `CANCELADA` / `DUPLICIDADE` entram.

### 3.2 Blocagem (quais pares chegam a ser comparados)

Comparar só pares com **mesma data**, ou com datas consecutivas quando a hora do sinistro
estiver perto da meia-noite. Sem isso seriam ~bilhões de pares; com isso, poucas dezenas
por sinistro.

### 3.3 Comparações por campo

| Campo | Comparação | Níveis (do mais forte ao mais fraco) |
|---|---|---|
| Hora | diferença em minutos, SAMU − CTTU | ≤ 15 min · ≤ 60 min · ≤ 180 min · resto |
| Bairro | igualdade após normalização | igual · vizinho (tabela de vizinhança a montar) · diferente |
| Endereço | similaridade de texto da via (Jaro-Winkler na rua normalizada, sem `AV`/`RUA`) ou distância entre pontos geocodificados | ≥ 0,9 · ≥ 0,75 · resto |
| Modal | `usuario_vulneravel` × categoria grossa do `subtipo` | compatível · desconhecido · incompatível |

Hora vazia ou inválida, bairro vazio etc. contam como **nível neutro** (peso 0), não como
discordância.

Os cortes acima são **ponto de partida, a calibrar** na amostra rotulada (3.5), não valores
validados.

### 3.4 Pesos e limiares

- Para cada nível, peso = log₂(m/u). **m** = P(nível | mesmo evento), **u** = P(nível |
  eventos diferentes). O u sai direto dos dados (pares aleatórios do mesmo bloco); o m sai
  da amostra rotulada ou de EM (a biblioteca Splink faz isso).
- Dois limiares: acima do superior → **provável**; entre os dois → **revisão manual**;
  abaixo do inferior → **não é par**.
- Atribuição **1:1**: um atendimento SAMU pode ter várias vítimas do mesmo sinistro (N
  atendimentos → 1 sinistro é válido), mas um atendimento não pode ir para dois sinistros.
  Fica o par de maior peso.

### 3.5 Validação (sem gabarito)

Não existe verdade de referência. Então:

1. Rotular à mão uma amostra estratificada (~200 pares, de todas as faixas de peso).
2. Reportar precisão estimada por faixa, **taxa de ambiguidade** (sinistros com mais de um
   candidato acima do limiar) e **taxa de não-pareamento** dos dois lados.
3. Todo resultado derivado (ex.: "% de sinistros com moto que geraram atendimento SAMU")
   vem com a faixa de incerteza e a descrição deste método ao lado (`06` #6).

### 3.6 Vieses já esperados

- **Geocodificação por trecho de rua:** a coordenada é um ponto da rua dentro do bairro;
  em avenidas longas, erro de quilômetros. Usar distância só como desempate.
- **A cobertura da CTTU cai muito a partir de 2020:** a taxa de pareamento vai mudar
  por isso, não necessariamente por mudança real.
- **Sinistros sem chamado à CTTU** (ex.: vítima levada por terceiros) nunca aparecem no
  pareamento. O não-pareamento mede o *sub-registro entre bases*, e não falha do método.

## 4. Pós-convênio: SAMU (microdados)

Com a ficha de atendimento, o cruzamento ganha horário de chegada ao local, endereço da
ocorrência mais preciso, condição da vítima e unidade de destino. O método da seção 3 é o
mesmo, com mais campos e pesos maiores. Campos exatos a confirmar quando houver acesso.

## 5. Pós-convênio: SDS

Os registros da SDS (BOs de trânsito, óbitos) trariam a **identificação da pessoa**, e o
cruzamento SDS × SAMU-microdados passaria a ser no nível da vítima (nome, nascimento,
sexo), não do evento. Isso exige:

- base legal pela LGPD, termo de uso e anonimização **antes** de os dados chegarem ao
  repositório;
- processamento em ambiente controlado, fora do git, com só os agregados saindo;
- cruzamento SDS × CTTU ainda pelo método da seção 3 (CTTU continua sem dado de pessoa).

Nada disso é necessário nem será feito no MVP.
