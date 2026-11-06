# 11 — Base limpa de atropelamentos (tarefa M1)

Uma linha por sinistro de atropelamento de pessoa no Recife, 2015–2024, com coordenada
vinda do semáforo informado no chamado (M1) ou da geocodificação do endereço (M1b). É a
entrada do modelo de risco (M4), que agrupa por `local_id`.

```bash
.venv/bin/python scripts/fetch_datasets.py          # 1. sinistros + semáforos
.venv/bin/python scripts/build_atropelamentos.py    # 2. gera a base (offline)
export NOMINATIM_CONTACT="seu-email@exemplo.com"
.venv/bin/python scripts/geocode_enderecos.py       # 3. único passo com internet (pula o que está no cache)
.venv/bin/python scripts/build_atropelamentos.py    # 4. gera a base de novo, com o cache
.venv/bin/python -m pytest                          # testes (sem internet)
```

Como o cache de geocodificação está no git, quem clona o repo normalmente pula o passo 3.

Saídas (fora do git, em `data/processed/`):

- `atropelamentos.parquet`: a base. As ressalvas abaixo vão também nos metadados do
  arquivo (chave `ressalvas`).
- `atropelamentos_qualidade.json`: relatório de cobertura e diagnóstico da fonte,
  regenerado a cada execução.
- `amostra_conferencia.csv`: 30 atropelamentos com coordenada (sorteio com seed 42), com
  link do OpenStreetMap e colunas vazias `conferido_ok` / `observacao` para o grupo
  conferir à mão.

No git, em `data/geocode/`: `cache_nominatim.csv`, uma linha por consulta feita ao
Nominatim (inclusive as que falharam).

## De onde vêm os dados

| Fonte (CKAN, licença ODbL) | Recurso | Uso |
|---|---|---|
| `acidentes-de-transito-com-e-sem-vitimas` | um CSV por ano, 2015–2024 | sinistros |
| `localizacao-dos-semaforos` | só **"Semáforos do Recife"** (712 semáforos) | lat/lon |
| Nominatim / OpenStreetMap (ODbL) | API de busca, via `geocode_enderecos.py` | lat/lon dos endereços |

Os outros três CSVs de semáforos (com sinalizador para ciclistas, iluminação suspensa para
pedestres, para deficientes visuais) são subconjuntos por tipo de equipamento e não são
usados. Os downloads passam por `ckan_client` + `manifest`; a URL assinada nunca é gravada.

As normalizações comuns aos CSVs de sinistros (colunas em minúsculas, `natureza_acidente`
→ `natureza`, troca `tipo`/`natureza` no CSV de 2015) ficam em `scripts/sinistros.py`,
compartilhado com `build_dashboard_data.py`.

## Regra de atropelamento

Uma linha entra na base se:

1. `tipo` contém `ATROPELAMENTO` **e não** contém `ANIMAL`; ou
2. `pedestre` > 0.

Valores de `tipo` encontrados (depois da troca de 2015):

| Valor | Anos | Entra? |
|---|---|---|
| `ATROPELAMENTO` | 2015–2021 | sim |
| `ATROPELAMENTO DE PESSOA` | 2021–2024 | sim |
| `ATROPELAMENTO ANIMAL` | 2015–2020 | não (só se `pedestre` > 0) |
| `ATROPELAMENTO DE ANIMAL` | 2021–2024 | não (só se `pedestre` > 0) |

`criterio_atropelamento` diz qual regra pegou a linha:

| Valor | Linhas | Leitura |
|---|---|---|
| `tipo+pedestre` | 1.940 | as duas regras concordam |
| `tipo` | 130 | tipo atropelamento, mas `pedestre` vazio ou 0 |
| `pedestre` | 95 | tipo é outro (39 `COLISÃO`, `QUEDA`, `COLISÃO COM CICLISTA`...), mas havia pedestre envolvido |

71 atropelamentos de animal ficaram de fora; 2 entraram por terem `pedestre` > 0.
Se a M4 quiser uma definição mais estrita, filtre `criterio_atropelamento != "pedestre"`.

## Colunas de saída

| Coluna | Tipo | Como é obtida |
|---|---|---|
| `protocolo` | texto | só existe de 2022 em diante (`"292972,0"` → `"292972"`); null antes. Sem duplicatas. |
| `data` | date | coluna `data` (`AAAA-MM-DD`) |
| `hora` | int 0–23 | hora de `hora` (`HH:MM:SS`); null se vazia ou inválida |
| `datahora` | timestamp | `data` + `HH:MM`, horário local do Recife sem fuso; null se `hora` é null |
| `ano`, `mes` | int | de `data` (não do nome do arquivo) |
| `dia_semana` | int | 0 = segunda … 6 = domingo |
| `faixa_horaria` | texto | blocos de 3 h: `00-03`, `03-06`, …, `21-24` |
| `natureza` | texto | como na fonte: `COM VÍTIMA`, `SEM VÍTIMA`, `VÍTIMA FATAL` ou null |
| `tipo` | texto | como na fonte |
| `bairro`, `endereco`, `bairro_cruzamento` | texto | como na fonte; `bairro_cruzamento` não existe em 2015 (null) |
| `numero` | texto | como na fonte, exceto `"229,0"` → `"229"` (artefato de exportação em 2022+) |
| `endereco_norm` | texto | maiúsculas, sem acento, sem pontuação, `AVENIDA`→`AV`, `RUA`→`R`, `ESTRADA`→`EST`, `PRACA`→`PCA`, espaços colapsados |
| `num_semaforo_norm` | texto | `"037"`, `"37,0"` → `"37"`; vazio, `0`, `S/N` → null. Coluna só existe de 2018 em diante |
| `pedestre`, `moto`, `ciclista`, `auto`, `onibus`, `caminhao` | int | contagens; **vazio → null** |
| `vitimas`, `vitimasfatais` | int | contagens; vazio → null; `vitimasfatais` null em todo 2015 (coluna não existe) |
| `gravidade` | texto | ver abaixo |
| `lat`, `lon` | float | coordenada final, escolhida pela prioridade da seção "Geocodificação" |
| `coord_fonte` | texto | `semaforo`, `endereco_numero`, `endereco_via`, `semaforo_nao_confere`, `endereco_nao_confere` ou null |
| `coord_precisao` | texto | `alta` (semaforo, endereco_numero), `media` (endereco_via), `baixa` (os dois `*_nao_confere`) ou null |
| `geo_display_name` | texto | endereço devolvido pelo Nominatim, quando a coordenada final vem dele |
| `lat_semaforo`, `lon_semaforo` | float | coordenada do semáforo, mantida separada para auditoria |
| `coord_confere` | bool | o semáforo bate com bairro ou rua do sinistro; null sem semáforo (ver abaixo) |
| `geo_nivel` | texto | resultado do geocode: `numero`, `via`, `outro`, `falhou` ou null (não consultado) |
| `geo_tentativa` | texto | consulta que deu o resultado usado: `a`, `b` ou `c` |
| `geo_bairro_confere`, `geo_rua_confere` | bool | o resultado do geocode está no bairro do sinistro / é a rua pedida |
| `local_id` | texto | ver abaixo |
| `criterio_atropelamento` | texto | ver acima |

### Contagens vazias ficam null, não zero

De 2015 a 2020 a fonte só preenche as contagens diferentes de zero (`pedestre`, `moto`
etc. vêm vazias quando não há o ator); de 2021 em diante vem `0` ou `0,0`. A base mantém o
vazio como null. Para "havia moto envolvida?", trate null como "não informado"; quem
quiser assumir zero deve fazer isso explicitamente na análise e dizer que fez.

### `gravidade`

Em ordem de precedência:

1. `fatal` se `natureza` = `VÍTIMA FATAL` ou `vitimasfatais` > 0;
2. `com_vitima` / `sem_vitima` conforme `natureza`;
3. se `natureza` está vazia: `com_vitima` se `vitimas` > 0;
4. `desconhecida` caso contrário.

Resultado: 2.043 `com_vitima`, 86 `fatal`, 33 `sem_vitima`, 3 `desconhecida`. A fonte se
contradiz em alguns casos (ex.: 31 atropelamentos `VÍTIMA FATAL` com `vitimas` = 0); a
`natureza` prevalece. "Sem vítima" num atropelamento é estranho, mas é o que a fonte diz —
não foi reclassificado.

## Coordenada por semáforo (M1)

Os sinistros não têm lat/lon. A primeira fonte é o semáforo informado em `num_semaforo`:
junção exata `num_semaforo_norm` = `semaforo_norm` (os dois lados sem zeros à esquerda e sem
`,0`), guardada em `lat_semaforo`/`lon_semaforo`. Linhas sem coordenada nenhuma ficam com
`lat`/`lon` null e continuam na base.

Ajustes no dataset de semáforos (registrados em `diagnostico_fonte.ajustes_semaforo` do JSON):

- Semáforo 693: latitude `-8.060979,` (vírgula sobrando no fim) → vírgula removida.
- Coordenadas fora de lat −8,30 a −7,80 / lon −35,10 a −34,80 seriam descartadas (hoje
  nenhuma, depois do ajuste acima).

`coord_confere` é um teste aproximado de que o semáforo informado é mesmo o local do
sinistro: `True` se o bairro do sinistro é igual ao do semáforo **ou** se alguma palavra do
`endereco` (≥ 3 letras, fora artigos e abreviações) aparece em `localizacao1`/`localizacao2`.
Na base inteira de sinistros, 95,5% dos 6.620 vínculos passam; entre os 250 atropelamentos
com coordenada, 7 não passam (ex.: `AV CRUZ CABUGA` ligada a um semáforo da Av. Boa Viagem).
A coordenada é mantida — o teste erra nos dois sentidos —, mas a M4 pode filtrar
`coord_confere == True`.

### `local_id`

- `sem-<número>` quando `num_semaforo_norm` existe no dataset de semáforos;
- `end-<slug de endereco_norm>-<slug do bairro>` caso contrário (`desconhecido` quando vazio).

Limitações para a M4:

- O mesmo cruzamento aparece como `end-...` em 2015–2017 (sem `num_semaforo`) e como
  `sem-...` depois. Agrupar por `local_id` sem tratar isso parte a série histórica do local.
- `end-...` junta a via inteira dentro do bairro (`end-av-caxanga-caxanga` tem 62
  atropelamentos), não um trecho. Não é a mesma granularidade de `sem-...`.
- 822 `local_id` distintos em 2.165 linhas.
- `local_id` não usa a coordenada geocodificada: o agrupamento espacial é tarefa da M4.

## Geocodificação (M1b)

Geocodificação © colaboradores do OpenStreetMap, ODbL.

### Método

`scripts/geocode_enderecos.py` é o único script da M1/M1b que acessa a internet. Ele
consulta o [Nominatim](https://nominatim.openstreetmap.org/) para cada combinação única de
(`endereco_norm`, `endereco`, `numero`, `bairro`) das linhas **sem** semáforo confirmado
(`coord_confere` diferente de `True`): 1.207 combinações em 2.165 linhas.

1. **Rua da consulta:** a abreviação inicial de `endereco_norm` é expandida (`AV`→Avenida,
   `R`→Rua, `EST`→Estrada, `PCA`/`PRC`→Praça, `TV`/`TRV`→Travessa, `PTE`→Ponte, `LGO`→Largo,
   `LAD`→Ladeira, `VDO`→Viaduto, `COR`→Corredor, `C`→Cais). Quando o `endereco` original já
   escreve o tipo por extenso e não tem abreviação com ponto (ex.: `RUA DIADEMA`), ele é usado
   no lugar.
2. **Tentativas** (`format=jsonv2`, `addressdetails=1`, `limit=1`, `countrycodes=br`, viewbox
   do Recife `-35.10,-7.80,-34.80,-8.30` com `bounded=1`):
   - (a) `street="<numero> <rua>"`, `city=Recife`, `state=Pernambuco`, só quando `numero` é
     um inteiro positivo (`XX`, `S/N`, `312A` não são enviados);
   - (b) a mesma consulta sem número;
   - (c) `q="<rua>, <bairro>, Recife, Pernambuco"`.

   Para no primeiro resultado. **Exceção:** se o resultado de (a) ou (b) não confere o bairro
   ou a rua (ver abaixo), (c) também é consultada, e o resultado de (c) é usado se ele
   conferir. Motivo: uma consulta só pela rua devolve um trecho qualquer da via. Em vias
   longas (Av. Beberibe, Estrada de Belém) ou com nome repetido em mais de um bairro
   (Rua do Sol), esse trecho costuma estar em outro bairro. Nessa base, (c) resolveu 183
   pares rua+bairro que (b) tinha colocado no bairro errado.
3. **Cache:** cada consulta vira uma linha em `data/geocode/cache_nominatim.csv`, com chave
   igual ao texto da consulta normalizado, tentativa, lat, lon, `display_name`, `osm_type`,
   `osm_id`, `class`, `type`, `bairro_retornado` (suburb/neighbourhood), o `addressdetails`
   completo (`componentes`), `nivel` e `consultado_em`. Falhas também ficam no cache, e nada
   é consultado duas vezes.
4. **Nível:** `numero` se o resultado tem `house_number`; `via` se é uma rua
   (`class=highway`); `outro` se é um lugar que não é nem um nem outro (ex.: um bairro);
   `falhou` se não achou nada.

**Política de uso do Nominatim:** no máximo 1 requisição por segundo; User-Agent com o
projeto e o contato lido de `NOMINATIM_CONTACT` (o script não roda sem ela); backoff com até
3 novas tentativas em 429/5xx; parada imediata em 403. O cache é salvo a cada 25 consultas e
no Ctrl+C, então o script pode ser interrompido e retomado. `--dry-run` mostra o que seria
consultado sem acessar a rede; `--limite N` processa só N endereços.

### Conferências

- **Bairro confere:** o `bairro` do sinistro, sem acento e em maiúsculas, é igual a algum
  nível abaixo da cidade no endereço devolvido (`suburb`, `neighbourhood`, `quarter`,
  `city_district`...) **ou** a alguma parte do `display_name`. O `display_name` entra porque o
  `addressdetails` guarda um só valor por nível. Na Rua Caburaí, por exemplo,
  `suburb` = "UR-07" (um conjunto habitacional) e o bairro oficial "Várzea" só aparece no
  `display_name`. "Recife" nunca conta como bairro.
- **Rua confere:** pelo menos metade das palavras significativas da rua pedida aparece no
  nome da rua devolvida, com tolerância a pequenas diferenças de grafia (`TAQUARITINGA` ×
  "Taquaratinga"). Foi necessária porque o Nominatim às vezes responde com outra rua
  ("RUA DA CUSTODIA" → "Rua Rosário de Minas"). Resultado com rua diferente **nunca** é
  usado: 44 linhas descartadas por isso.

### Prioridade da coordenada final

| # | Condição | `coord_fonte` | `coord_precisao` | Linhas |
|---|---|---|---|---|
| 1 | semáforo com `coord_confere == True` | `semaforo` | alta | 243 |
| 2 | geocode nível `numero` com bairro conferindo | `endereco_numero` | alta | 257 |
| 3 | geocode nível `via` com bairro conferindo | `endereco_via` | media | 1.402 |
| 4 | semáforo com `coord_confere == False` | `semaforo_nao_confere` | baixa | 2 |
| 5 | geocode sem bairro conferindo (inclui nível `outro`) | `endereco_nao_confere` | baixa | 161 |
| 6 | nada disso | null | null | 100 |

Em todos os casos geocodificados, a rua precisa conferir. Das 100 linhas sem coordenada, 53
são endereços que o Nominatim não achou, 43 só tinham resultado com rua diferente e 4 não
têm endereço. Os endereços que mais falharam (`top20_enderecos_que_falharam` no JSON) são
`R PRINCESA IZABEL` (9), `R EXP FRANCISCO VITORIANO` (5), `AV DES GUERRA BARRETO` (4),
`AV CELSO FURTADO VIA MANGUE` (4) e `COR DO BARTOLOMEU` (4). Em geral, são abreviações de
título no meio do nome (`EXP`, `DES`, `N S`) ou nomes compostos.

### Cobertura antes e depois (execução de 06/11/2026)

| Ano | Atropelamentos | Com coordenada antes (só semáforo) | Com coordenada depois | Precisão alta ou média |
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
| **Total** | **2.165** | **11,5%** | **95,4%** | **87,8%** |

O JSON de qualidade traz sempre os números atuais (`pct_com_coordenada_antes_geocode_por_ano`,
`pct_com_coordenada_por_ano`, `pct_precisao_alta_ou_media_por_ano`, `por_coord_fonte`,
`por_coord_precisao`). Esta tabela é um retrato.

### Limitações

- **Um ponto "via" é o centro aproximado de um trecho da rua, não o local do sinistro.**
  São 1.402 linhas (65%), e o número digitado, quando existe, raramente é achado: só 257
  linhas chegam ao nível `numero`.
- **Vias longas:** mesmo com o bairro conferindo, o trecho devolvido pode estar a centenas de
  metros, ou mais de 1 km, do ponto real. Exemplos são a Av. Caxangá, a Av. Recife e a Av.
  Norte, que atravessam vários bairros.
- **Muitos sinistros no mesmo ponto:** todos os atropelamentos de uma mesma rua e bairro com
  nível `via` recebem a mesma coordenada. As 2.065 linhas com coordenada ocupam só 970 pontos
  distintos. Mapas de calor e clusters vão mostrar "pilhas" artificiais nesses pontos.
- **"Bairro confere" não é prova de acerto.** É só um sinal de plausibilidade: bairros
  vizinhos e limites diferentes entre CTTU e OSM geram falsos negativos, e uma rua homônima no
  mesmo bairro geraria um falso positivo. A amostra de conferência existe para medir isso à mão.
- **O OSM muda.** Repetir as consultas no futuro pode dar outro resultado. O cache, com
  `consultado_em`, é o que garante que a base é reproduzível.
- **Atribuição:** qualquer mapa ou material que use estas coordenadas deve citar
  "Geocodificação © colaboradores do OpenStreetMap, ODbL".

## Cobertura só por semáforo (M1, execução de 05/11/2026)

| Ano | Atropelamentos | Com coordenada | Hora válida |
|---|---|---|---|
| 2015 (jun–dez) | 165 | 0,0% | 100,0% |
| 2016 | 262 | 0,0% | 100,0% |
| 2017 | 282 | 0,0% | 100,0% |
| 2018 | 224 | 5,8% | 99,6% |
| 2019 | 263 | 23,6% | 100,0% |
| 2020 | 155 | 30,3% | 100,0% |
| 2021 | 163 | 28,8% | 100,0% |
| 2022 | 211 | 26,1% | **0,0%** |
| 2023 | 228 | 7,5% | 100,0% |
| 2024 | 212 | 4,2% | 100,0% |
| **Total** | **2.165** | **11,5%** (250) | **90,2%** |

Mantida como registro da M1. A coluna equivalente hoje é
`pct_com_coordenada_antes_geocode_por_ano` do JSON.

Leitura: a coordenada por semáforo cobre pouco e de forma enviesada. Pega só cruzamentos
semaforizados, e quase nada em 2018, 2023 e 2024, quando `num_semaforo` foi pouco preenchido
(6%, 8,5% e 3,7% de todos os sinistros). Um mapa feito só com ela mostra **onde há
semáforo**, não onde há mais atropelamento. Por isso foi feita a geocodificação da M1b.

## Ressalvas que se aplicam

1. **2015 só a partir de junho** (confirmado: datas de 2015-06-01 a 2015-12-31). Total anual de
   2015 subestimado.
2. **"Chamados" ≠ relatórios oficiais.** O portal diz que os dados "são referentes aos
   chamados e podem diferir dos dados divulgados nos relatórios anuais", que usam registros
   estatísticos dos agentes de trânsito. Nenhuma contagem desta base deve ser rotulada como
   número oficial do PSVR.
3. **2025 é preliminar.** A base não tem atropelamentos de 2025. O CSV de 2024 traz 36
   sinistros datados de 29–31/12/2025 (nenhum atropelamento); como todos têm protocolo
   começando por `2024` e o mês de dez/2024 do arquivo termina no dia 28, é provável que sejam
   de 29–31/12/2024 com o ano digitado errado. **Não foram corrigidos**: ficam com a data da
   fonte e são contados em `diagnostico_fonte.linhas_com_ano_diferente_do_arquivo_toda_base`.
4. **`vitimasfatais` não existe em 2015** — null, nunca zero. `gravidade` = `fatal` em 2015 vem
   só de `natureza`.
5. **Queda de registros a partir de 2020.** Verificado na fonte inteira (não só atropelamentos):

   | Ano | SEM VÍTIMA | COM VÍTIMA | Atropelamentos (esta base) |
   |---|---|---|---|
   | 2019 | 9.796 | 2.235 | 263 |
   | 2020 | 2.317 | 1.754 | 155 |
   | 2021 | 540 | 1.809 | 163 |
   | 2024 | 610 | 4.671 | 212 |

   A queda é quase toda em `SEM VÍTIMA` e é abrupta: 851 em mar/2020, 21 em abr/2020, e não
   volta (30–80 por mês até 2024). `COM VÍTIMA` cai menos em 2020 e depois cresce até o dobro.
   O começo coincide com a pandemia, mas o fato de não haver recuperação aponta para mudança
   no que é registrado como chamado (cobertura parcial da fonte para sinistros sem vítima),
   não para queda real de sinistros. **A fonte não explica a causa** — isso é hipótese, a
   confirmar com a CTTU. Para atropelamentos (quase sempre com vítima) o efeito é menor, mas
   2020–2021 ainda ficam abaixo de 2019, e parte disso pode ser pandemia.
6. **Hora vazia em todo o CSV de 2022** (2.669 sinistros). `hora`, `datahora` e `faixa_horaria`
   são null nesse ano; qualquer análise por horário usa só os outros anos.
7. **Ausência de geolocalização** (docs/06 #7) e **sem chave de junção entre bases** (#6): a
   fonte não traz o ponto exato de nenhum sinistro. A coordenada de semáforo é a do semáforo
   informado no chamado, com vínculo por número digitado e sujeito a erro (ver
   `coord_confere`). A coordenada geocodificada é, na maioria dos casos, um trecho da rua
   (ver "Geocodificação → Limitações"). Filtre por `coord_precisao` conforme a análise.
8. **Mudança de formulário** (docs/06 #9): `protocolo` só a partir de 2022; `num_semaforo` só a
   partir de 2018; contagens vazias até 2020 vs. `0` depois; vocabulário de `tipo` muda em
   2018 e 2021. Linhas com lixo no `tipo` (`NATUREZA`, `SANTO AMARO`, `0`...) não são
   atropelamento e não entram; horas inválidas (`CITTAMOBI`, `29208:00:00`...) viram null.
