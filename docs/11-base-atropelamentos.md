# 11 — Base de sinistros e geocodificação

Pipeline que transforma os CSVs de sinistros da CTTU (2015–2024) numa base com coordenadas,
carregada no PostGIS e usada pelo modelo de risco (M4). O mesmo pipeline atende a análise de
todos os sinistros e a de atropelamentos (flag `atropelamento`). Ele junta duas frentes que
corriam em paralelo: o pipeline de limpeza e PostGIS do Guilherme (`feat/sinistros-postgis-risco`)
e a geocodificação conferida do M1/M1b (preservada na tag `backup-marina-m1-m1b`).

```bash
.venv/bin/python scripts/fetch_datasets.py --dataset sinistros     # 1. sinistros 2015–2024 (CKAN)
.venv/bin/python scripts/fetch_datasets.py --dataset semaforos     #    só o recurso "Semáforos do Recife"
.venv/bin/python scripts/clean_sinistros.py                        # 2. limpeza (offline)
.venv/bin/python scripts/geocode_sinistros.py --offline            # 3a. só aplica o cache versionado
export NOMINATIM_CONTACT="seu-email@exemplo.com"                   #     contato exigido pelo Nominatim
.venv/bin/python scripts/geocode_sinistros.py                      # 3b. geocodifica o que falta (internet, lento)
scripts/load_postgis.sh                                            # 4. PostGIS, risco, validação, trechos.json
.venv/bin/python -m pytest                                         # testes (sem internet)
```

| Etapa | Script | Saída | No git? |
|---|---|---|---|
| Limpeza | `clean_sinistros.py` | `data/processed/sinistros/sinistros_2015_2024.parquet` + `README.md` | não |
| Geocodificação | `geocode_sinistros.py` | `sinistros_2015_2024_geo.parquet` + `README_geocodificacao.md` + `amostra_conferencia.csv` | não |
| Cache do Nominatim | `geocode_sinistros.py` | `data/geocode/cache_nominatim.csv` | **sim** |
| Carga e risco | `load_postgis.sh`, `sql/01`–`03` | tabelas `sinistros`, `risco_atual`, `risco_horario`, `validacao_m4` | — |
| Trechos (contrato) | `sql/04_trechos.sql` | `data/contrato/trechos.json` (docs/09, parte 1) | **sim** |

As ressalvas da seção final vão também nos metadados do parquet geocodificado (chave
`ressalvas`), no README gerado e no `COMMENT` da tabela `sinistros`.

## De onde vêm os dados

| Fonte | Recurso | Uso |
|---|---|---|
| `acidentes-de-transito-com-e-sem-vitimas` (CKAN, ODbL) | um CSV por ano, 2015–2024 | sinistros |
| `localizacao-dos-semaforos` (CKAN, ODbL) | só **"Semáforos do Recife"** (712 semáforos) | lat/lon por `num_semaforo` |
| Nominatim / OpenStreetMap (ODbL) | API de busca | lat/lon dos endereços |

Os outros três CSVs de semáforos (com sinalizador para ciclistas, iluminação suspensa para
pedestres, para deficientes visuais) são subconjuntos por tipo de equipamento e não são
baixados (`RESOURCE_FILTER` em `fetch_datasets.py`). Os downloads passam por `ckan_client` +
`manifest`, e a URL assinada nunca é gravada. O manifesto baixa de novo quando o arquivo
local não existe (clone novo).

## Limpeza (`clean_sinistros.py`)

Uma linha por **chamado**, nenhuma linha descartada. O README gerado tem a lista completa de
normalizações. Resumo:

- colunas unificadas entre anos; no CSV de 2015, `tipo`/`natureza` estão trocadas na fonte e
  são destrocadas aqui (`gravidade`, `tipo_acidente`);
- `hora` → `HH:MM:SS`, texto inválido vira NA com `hora_invalida=True`;
- números `"1,0"` → inteiro; uma coluna ausente num ano (ex.: `vitimasfatais` em 2015) fica NA,
  nunca zero;
- `bairro`: grafias que só diferem em acento/espaço são unificadas (original em `bairro_original`);
- `data_fora_do_ano_arquivo` marca as datas fora do ano do arquivo (sem corrigir).

### Regra de atropelamento

- `atropelamento` (flag usada no M4): `tipo_acidente` começa com `ATROPELAMENTO` e não contém
  `ANIMAL`. **2.070 linhas.**
- `criterio_atropelamento` (informativa) diz por qual regra a linha seria atropelamento:

| Valor | Linhas | Leitura |
|---|---|---|
| `tipo+pedestre` | 1.940 | as duas regras concordam |
| `tipo` | 130 | tipo atropelamento, mas `pedestre` vazio ou 0 |
| `pedestre` | 95 | tipo é outro (39 `COLISÃO`, `QUEDA`, `COLISÃO COM CICLISTA`...), mas havia pedestre envolvido |
| null | resto | nenhuma das duas |

Valores de `tipo` encontrados: `ATROPELAMENTO` (2015–2021) e `ATROPELAMENTO DE PESSOA`
(2021–2024) entram; `ATROPELAMENTO ANIMAL` (2015–2020) e `ATROPELAMENTO DE ANIMAL` (2021–2024)
não. 71 atropelamentos de animal ficam de fora, e 2 deles têm `pedestre` > 0 (aparecem como
`pedestre`). Quem quiser a definição ampla do M1 (2.165 linhas) usa
`criterio_atropelamento IS NOT NULL` e diz que fez.

### Contagens vazias ficam null, não zero

De 2015 a 2020, a fonte só preenche as contagens diferentes de zero: `pedestre`, `moto` etc.
vêm vazias quando não há o ator. De 2021 em diante vem `0` ou `0,0`. As colunas de veículo
contam **participantes, não vítimas**.

## Geocodificação (`geocode_sinistros.py`)

Geocodificação © colaboradores do OpenStreetMap, ODbL.

### 1. Semáforo

`num_semaforo` (só existe de 2018 em diante) é normalizado (`"037"`, `"37,0"` → `"37"`;
vazio, `0`, `S/N` → null) e ligado exatamente ao semáforo de mesmo número. Ajustes no dataset
de semáforos, registrados no README gerado:

- Semáforo 693: latitude `-8.060979,` (vírgula sobrando no fim) → vírgula removida.
- Coordenadas fora de lat −8,30 a −7,80 / lon −35,10 a −34,80 são descartadas (hoje nenhuma).

`coord_confere` testa se o semáforo informado é plausivelmente o local do sinistro. É `True`
se o bairro do sinistro é igual ao do semáforo **ou** se alguma palavra do `endereco`
(≥ 3 letras, fora artigos e abreviações) aparece em `localizacao1`/`localizacao2`. Na base
inteira, 95,5% dos 6.620 vínculos passam. **O semáforo só tem prioridade quando confere.**
Quando não confere (ex.: `AV CRUZ CABUGA` ligada a um semáforo da Av. Boa Viagem), a coordenada
do semáforo só é usada se a geocodificação não achar nada melhor.

### 2. Nominatim

Só as linhas **sem** semáforo conferindo são geocodificadas, uma vez por combinação única de
(`endereco_norm`, `endereco`, `numero`, `bairro`).

1. **Rua da consulta:** `endereco_norm` (maiúsculas, sem acento, sem pontuação, `AVENIDA`→`AV`,
   `RUA`→`R`, `ESTRADA`→`EST`, `PRACA`→`PCA`) tem a abreviação inicial expandida (`AV`→Avenida,
   `R`→Rua, `EST`→Estrada, `PCA`/`PRC`→Praça, `TV`/`TRV`/`TRAV`→Travessa, `PTE`→Ponte,
   `LGO`→Largo, `LAD`→Ladeira, `VDO`/`VD`→Viaduto, `COR`→Corredor, `C`→Cais, `ROD`→Rodovia,
   `AL`→Alameda, `PRQ`→Parque). Quando o `endereco` já escreve o tipo por extenso e não tem
   abreviação com ponto (ex.: `RUA DIADEMA`), ele é usado no lugar.
2. **Tentativas** (`format=jsonv2`, `addressdetails=1`, `limit=1`, `countrycodes=br`, viewbox
   do Recife `-35.10,-7.80,-34.80,-8.30` com `bounded=1`):
   - (a) `street="<numero> <rua>"`, `city=Recife`, `state=Pernambuco`, só quando `numero` é um
     inteiro positivo (`XX`, `S/N`, `312A` não são enviados);
   - (b) a mesma consulta sem número;
   - (c) `q="<rua>, <bairro>, Recife, Pernambuco"`.

   O script para no primeiro resultado, com uma **exceção**: se o resultado de (a) ou (b) não
   confere o bairro ou a rua, (c) também é consultada e é usada se conferir. Uma consulta só
   pela rua devolve um trecho qualquer da via. Em vias longas (Av. Beberibe, Estrada de Belém)
   ou com nome repetido (Rua do Sol), esse trecho costuma cair em outro bairro. Nos
   atropelamentos, (c) corrigiu 183 pares rua+bairro que (b) tinha posto no bairro errado.
3. **Nível:** `numero` se o resultado tem `house_number`; `via` se é uma rua (`class=highway`);
   `outro` se é outro lugar (ex.: um bairro); `falhou` se não achou nada.

**Conferências.**

- **Bairro confere:** o `bairro` do sinistro (sem acento, maiúsculas) é igual a algum nível
  abaixo da cidade no endereço devolvido (`suburb`, `neighbourhood`, `quarter`,
  `city_district`...) **ou** a alguma parte do `display_name`. Isso é necessário porque o
  `addressdetails` guarda um só valor por nível. Na Rua Caburaí, por exemplo, `suburb` é
  "UR-07" e "Várzea" só aparece no `display_name`. "Recife" nunca conta como bairro.
- **Rua confere:** pelo menos metade das palavras significativas da rua pedida aparece no nome
  da rua devolvida, com tolerância a grafia (`TAQUARITINGA` × "Taquaratinga"). O Nominatim às
  vezes responde com outra rua ("RUA DA CUSTODIA" → "Rua Rosário de Minas"). Resultado com rua
  diferente **nunca** é usado: 44 atropelamentos foram descartados por isso.

**Política de uso do Nominatim.** No máximo 1 requisição/s. O User-Agent leva o projeto e o
contato lido de `NOMINATIM_CONTACT`, e o script não consulta a rede sem ela. Em 429/5xx há
backoff com até 3 novas tentativas, e em 403 o script para na hora. Cache salvo a cada 25
consultas e no Ctrl+C. Flags: `--offline` (só aplica o cache), `--dry-run`, `--limite N`.

### 3. Cache versionado

`data/geocode/cache_nominatim.csv` tem uma linha por consulta já feita, inclusive as que
falharam: chave = texto da consulta normalizado, tentativa, lat, lon, `display_name`,
`osm_type`, `osm_id`, `class`, `type`, `bairro_retornado`, `addressdetails` completo
(`componentes`), `nivel` e `consultado_em`. O arquivo está no git, então ninguém repete uma
consulta. Ele traz as 1.427 consultas do M1b, e todas continuam alcançáveis pelo pipeline
integrado.

O cache antigo do pipeline do Guilherme (`data/processed/sinistros/geocode_cache.json`,
chave `"ENDERECO|BAIRRO"`, fora do git) pode ser importado com
`geocode_sinistros.py --importar-cache-json`:

- `via_bairro` → consulta (c);
- `via` → consulta (b), com (c) marcada como falha;
- `null` → (b) e (c) falharam.

Esse cache não tem `addressdetails`, então as conferências usam só o `display_name`. Linhas
já existentes nunca são sobrescritas.

### 4. Prioridade da coordenada final

| # | Condição | `geo_precisao` | `coord_precisao` |
|---|---|---|---|
| 1 | semáforo com `coord_confere == True` | `semaforo` | alta |
| 2 | geocode nível `numero`, bairro e rua conferindo | `endereco_numero` | alta |
| 3 | geocode nível `via`, bairro e rua conferindo | `endereco_via` | media |
| 4 | semáforo com `coord_confere == False` | `semaforo_nao_confere` | baixa |
| 5 | geocode com rua conferindo e bairro não (inclui nível `outro`) | `endereco_nao_confere` | baixa |
| 6 | nada disso | null | null |

Colunas de auditoria: `lat_semaforo`, `lon_semaforo`, `coord_confere`, `geo_nivel`,
`geo_tentativa`, `geo_bairro_confere`, `geo_rua_confere`, `geo_display_name`, `endereco_norm`,
`num_semaforo_norm`.

**O M4 usa só `coord_precisao` alta ou média** (`sql/02_risco.sql`).

### Cobertura (execução de 06/11/2026, só com o cache do M1b)

O cache cobre todos os atropelamentos. Para os demais sinistros, faltam 22.506 endereços
(~7–14 h de Nominatim a 1 req/s), então os números de "todos" abaixo **vão mudar** depois do
geocode completo.

Atropelamentos (regra ampla, 2.165 linhas): 1.402 `endereco_via`, 257 `endereco_numero`,
243 `semaforo`, 161 `endereco_nao_confere`, 2 `semaforo_nao_confere`, 100 sem coordenada.
95,4% têm coordenada e 87,9% têm precisão alta ou média. Na flag `atropelamento` (2.070
linhas), são 1.339 / 250 / 232 / 157 / 2 / 90.

| Ano | Atropelamentos | Com coordenada (só semáforo) | Com coordenada (final) | Alta ou média |
|---|---|---|---|---|
| 2015 (jun–dez) | 165 | 0,0% | 95,2% | 86,1% |
| 2016 | 262 | 0,0% | 95,0% | 88,5% |
| 2017 | 282 | 0,0% | 96,1% | 84,8% |
| 2018 | 224 | 5,8% | 95,5% | 84,8% |
| 2019 | 263 | 23,6% | 97,7% | 90,9% |
| 2020 | 155 | 30,3% | 91,6% | 85,8% |
| 2021 | 163 | 28,8% | 96,9% | 92,0% |
| 2022 | 211 | 26,1% | 97,2% | 92,9% |
| 2023 | 228 | 7,5% | 93,9% | 86,8% |
| 2024 | 212 | 4,2% | 93,4% | 86,3% |
| **Total** | **2.165** | **11,5%** | **95,4%** | **87,9%** |

Todos os sinistros (72.255): 9,2% têm coordenada só por semáforo e 47,0% depois do cache
atual. A tabela por ano fica no `README_geocodificacao.md` gerado.

Leitura da coluna "só semáforo": essa coordenada cobre pouco e de forma enviesada. Pega só
cruzamentos semaforizados, e quase nada em 2018, 2023 e 2024, quando `num_semaforo` foi pouco
preenchido (6%, 8,5% e 3,7% de todos os sinistros). Um mapa feito só com ela mostra **onde há
semáforo**, não onde há mais sinistro.

### Limitações da geocodificação

- **Um ponto `endereco_via` é o centro aproximado de um trecho da rua, não o local do
  sinistro.** É o caso de 65% dos atropelamentos. O número digitado, quando existe, raramente
  é achado.
- **Vias longas:** mesmo com o bairro conferindo, o ponto pode estar a centenas de metros, ou a
  mais de 1 km, do local real (Av. Caxangá, Av. Recife, Av. Norte).
- **Pilhas de pontos no nível `via`:** todos os sinistros de uma mesma rua e bairro com nível
  `via` recebem a mesma coordenada. Nos atropelamentos, 2.065 linhas com coordenada ocupam só
  970 pontos distintos. Em todos os sinistros, hoje são 33.975 linhas em 1.533 pontos. Mapas de
  calor e o DBSCAN do M4 enxergam essas "pilhas" artificiais: um único ponto `via` com ≥
  `min_pts` sinistros já vira cluster. Por isso o `raio_m` dos trechos tem piso de 200 m e a
  validação usa 500 m.
- **"Bairro confere" não é prova de acerto**, só um sinal de plausibilidade. Bairros vizinhos e
  limites diferentes entre CTTU e OSM geram falsos negativos, e uma rua homônima no mesmo bairro
  geraria um falso positivo. `amostra_conferencia.csv` (30 atropelamentos, seed 42, com link OSM
  e colunas `conferido_ok`/`observacao`) existe para medir isso à mão.
- **O OSM muda.** Repetir as consultas pode dar outro resultado. O cache, com `consultado_em`, é
  o que torna a base reproduzível.
- Os endereços que mais falham são abreviações de título no meio do nome ou nomes compostos:
  `R PRINCESA IZABEL`, `R EXP FRANCISCO VITORIANO`, `AV DES GUERRA BARRETO`,
  `AV CELSO FURTADO VIA MANGUE`, `COR DO BARTOLOMEU`, entre outros.
- **Atribuição:** qualquer mapa ou material que use estas coordenadas deve citar
  "Geocodificação © colaboradores do OpenStreetMap, ODbL".

## Ressalvas da fonte (não remover)

1. **2015 só a partir de junho** (datas de 2015-06-01 a 2015-12-31). O total anual de 2015
   está subestimado.
2. **"Chamados" ≠ relatórios oficiais.** O portal diz que os dados "são referentes aos chamados
   e podem diferir dos dados divulgados nos relatórios anuais", que usam registros estatísticos
   dos agentes. Nenhuma contagem desta base é número oficial do PSVR.
3. **2025 é preliminar.** O CSV de 2024 traz **36 sinistros datados de 29–31/12/2025** (nenhum
   atropelamento). Todos têm protocolo começando por `2024`, e o mês de dez/2024 do arquivo
   termina no dia 28, então o provável é que sejam de 29–31/12/2024 com o ano digitado errado.
   **Não foram corrigidos:** ficam com a data da fonte, com `data_fora_do_ano_arquivo=True`, e o
   M4 os exclui.
4. **`vitimasfatais` não existe em 2015**: fica null, nunca zero.
5. **Queda de registros a partir de 2020.** Verificado na fonte inteira:

   | Ano | SEM VÍTIMA | COM VÍTIMA | Atropelamentos (regra ampla) |
   |---|---|---|---|
   | 2019 | 9.796 | 2.235 | 263 |
   | 2020 | 2.317 | 1.754 | 155 |
   | 2021 | 540 | 1.809 | 163 |
   | 2024 | 610 | 4.671 | 212 |

   A queda é quase toda em `SEM VÍTIMA` e é abrupta: 851 registros em mar/2020, 21 em abr/2020,
   e o número não volta (30–80 por mês até 2024). `COM VÍTIMA` cai menos e depois cresce até o
   dobro. O início coincide com a pandemia, mas a falta de recuperação aponta para mudança no que
   é registrado, não para queda real. **A fonte não explica a causa**: é hipótese, a confirmar
   com a CTTU. Para o M4, isso significa que os anos depois de 2020 têm menos sinistros leves, e
   o peso de recência (meia-vida de 2 anos) puxa o score para os anos de cobertura menor.
6. **Hora vazia em todo o CSV de 2022** (2.669 sinistros). Análises por horário, incluindo o
   campo `horas` dos trechos, usam só os outros anos.
7. **`num_semaforo` só desde 2018:** 2015–2017 não têm coordenada por semáforo.
8. **Ausência de geolocalização** (docs/06 #7) e **sem chave de junção entre bases** (#6): a
   fonte não traz o ponto exato de nenhum sinistro. Filtre por `coord_precisao`.
9. **Mudança de formulário** (docs/06 #9): `protocolo` só a partir de 2022; contagens vazias até
   2020 vs. `0` depois; vocabulário de `tipo` muda em 2019/2021; colunas de contexto só
   preenchidas de 2018 a 2022. Linhas com lixo em `tipo` (`NATUREZA`, `SANTO AMARO`, `0`...)
   não são atropelamento; horas inválidas (`CITTAMOBI`, `29208:00:00`...) viram null.
10. `situacao` inclui `CANCELADA` e `DUPLICIDADE`: as linhas ficam na base e o M4 as exclui.
