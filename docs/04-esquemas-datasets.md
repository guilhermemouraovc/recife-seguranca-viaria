# 04 — Esquemas reais dos datasets

Colunas confirmadas inspecionando diretamente as primeiras linhas de cada CSV em
14/08/2026 (não confiar cegamente em nomes de coluna "óbvios" — vários têm ambiguidade,
documentada abaixo). Separador `;`, valores numéricos usam vírgula decimal em alguns
datasets (herança de planilha em pt-BR) — atenção ao fazer parsing.

## Sinistros (`acidentes-de-transito-{ano}.csv`)

Separador `;`, aspas duplas, números com vírgula decimal (`"1,0"` = 1).

```
Protocolo; data; hora; natureza; situacao; bairro; endereco; numero;
detalhe_endereco_acidente; complemento; bairro_cruzamento; num_semaforo; sentido_via; tipo;
auto; moto; ciclom; ciclista; pedestre; onibus; caminhao; viatura; outros; vitimas;
vitimasfatais; acidente_verificado; tempo_clima; situacao_semaforo; sinalizacao;
condicao_via; conservacao_via; ponto_controle; situacao_placa; velocidade_max_via;
mao_direcao; divisao_via1; divisao_via2
```

Notas:
- `natureza`: observado `"COM VÍTIMA"` — confirmar os demais valores possíveis (deveria
  incluir `"SEM VÍTIMA"` dado o nome do dataset).
- `auto`, `moto`, `ciclom`, `ciclista`, `pedestre`, `onibus`, `caminhao`, `viatura`,
  `outros`: contagem de veículos/atores envolvidos por tipo, não flags binárias — somar por
  sinistro para saber quantos "participantes" teve.
- `vitimas` e `vitimasfatais`: contagens agregadas do sinistro, não uma linha por vítima.
- Muitas colunas de contexto (`tempo_clima`, `situacao_semaforo`, `sinalizacao`,
  `condicao_via`, `conservacao_via`, `ponto_controle`, `situacao_placa`,
  `velocidade_max_via`, `mao_direcao`, `divisao_via1/2`) vieram **vazias na amostra
  inspecionada** (2024) — checar se são preenchidas em outros anos ou se estão
  sistematicamente em branco (mudança de formulário de coleta ao longo do tempo é comum
  nesse tipo de base pública).

## Infrações de trânsito (`registro-das-infracoes-de-transito-{ano}.csv`)

```
datainfracao; horainfracao; dataimplantacao; agenteequipamento; infracao;
descricaoinfracao; amparolegal; localcometimento
```

- `agenteequipamento`: texto livre tipo `"Código 8 - AUTOS NO TALÃO ELETRÔNICO"` — não é o
  ID do equipamento (esse ID está no dataset de equipamentos); tratar como categoria do
  tipo de fiscalização, não como chave de junção.
- `localcometimento`: endereço em texto livre, mesmo problema de geocodificação do dataset
  de sinistros.
- Há dicionário de dados oficial em PDF e JSON (`Dicionário de Dados das Infrações de
  trânsito`) — usar para confirmar os códigos de infração antes de qualquer análise.

## Velocidade das vias (`{lombadas|fotossensores}-{ano}-{mes}-quantitativo-das-vias-por-velocidade-media.csv`)

```
ano; mes; equipamento; faixa; data; hora; minutos_intervalo; qtd_0a10km; qtd_11a20km;
qtd_21a30km; qtd_31a40km; qtd_41a50km; qtd_51a60km; qtd_61a70km; qtd_71a80km; qtd_81a90km;
qtd_91a100km; qtd_acimade100km
```

- `equipamento`: numérico, deveria bater com `identificacao_equipamento` do dataset de
  Equipamentos — **confirmar o tipo de dado e formatação (zero-padding?) antes de fazer o
  join**, não assumir compatibilidade direta de string vs. número.
- `hora`: valor inteiro observado (`0`, `10`...), parece ser a hora cheia; o intervalo real
  de 15 minutos está em `minutos_intervalo` (texto tipo `"00:00-00:15"`).
- Volume de dados alto (dezenas de recursos por ano, cada um potencialmente com milhares de
  linhas) — não carregar tudo em memória de uma vez; processar por arquivo/mês.

## Equipamentos de fiscalização (`lista-de-equipamentos-de-fiscalizacao-de-transito.csv`)

```
tipo_equipamento; registro_inmetro; numero_serie_fabricante; identificacao_equipamento;
local_instalacao; sentido_fiscalizacao; latitude; longitude; faixas_fiscalizadas;
velocidade_fiscalizada; vmd; periodo_vmd
```

- **Corrupção de encoding confirmada na fonte** (não é erro de download): endereços como
  `"AV. ENG. JOS\x90 ESTELITA, APàS PTE. AGAMENON MAGALHAES"` (deveria ser "ENG. JOSÉ
  ESTELITA, APÓS..."). Ver `06-limitacoes-metodologicas.md` para como tratar.
- `vmd` (volume médio diário) e `periodo_vmd` (ex.: `"set/25"`) indicam que o VMD é uma
  medição pontual desatualizada rapidamente, não uma série temporal — não tratar como
  contagem atual.

## Semáforos (`semaforos-do-recife.csv`)

```
semaforo; localizacao1; localizacao2; bairro; latitude; longitude; tipo; funcionamento;
Unnamed: 8
```

- Última coluna sem nome (`Unnamed: 8`, valor `"1"` observado) — provavelmente artefato de
  exportação de planilha; investigar antes de descartar (pode ser um flag de status).

## SAMU (`solicitacoes-de-atendimento-{ano}.csv`)

Separador `;` sem aspas nas primeiras linhas observadas (confirmar se todos os anos seguem o
mesmo padrão de quoting).

```
data; hora_minuto; municipio; bairro; endereco; origem_chamado; tipo; subtipo; sexo; idade;
motivo_finalizacao; motivo_desfecho
```

- `municipio`: cobre toda a Região Metropolitana (`RECIFE`, `POMBOS`, `PAULISTA`,
  `JABOATAO DOS GUARARAPES` observados na amostra) — **filtrar por `RECIFE`** quando o
  recorte for a cidade.
- `tipo`/`subtipo`: é aqui que mora o recorte de trânsito — ex. `tipo="CAUSAS EXTERNAS"`,
  `subtipo="ACIDENTE DE TRANSITO ENVOLVENDO MOTO"`. Levantar o dicionário completo de
  valores de `subtipo` antes de decidir o filtro (busca por `"TRANSITO"` no subtipo é o
  ponto de partida, mas pode haver variações de grafia).
- Dicionário de dados oficial disponível em JSON por ano (`Dicionário de Dados - Chamados
  Samu {ano}`) — usar para confirmar os valores categóricos válidos de `tipo`/`subtipo`.

## PDFs institucionais

PSVR e Relatórios Anuais são texto corrido + tabelas, não têm "schema" tabular. Ao
extrair, priorizar: (a) as tabelas de metas/indicadores do PSVR (eixos, iniciativas, ações,
indicadores), (b) as séries históricas de mortes/feridos por ano presentes nos Relatórios
Anuais, quando existirem em formato de tabela dentro do PDF.
