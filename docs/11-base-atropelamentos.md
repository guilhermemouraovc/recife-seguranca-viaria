# 11 — Base limpa de atropelamentos (tarefa M1)

Uma linha por sinistro de atropelamento de pessoa no Recife, 2015–2024, com coordenada
quando ela pode ser obtida sem geocodificador. É a entrada do modelo de risco (M4), que
agrupa por `local_id`.

```bash
.venv/bin/python scripts/fetch_datasets.py          # sinistros + semáforos
.venv/bin/python scripts/build_atropelamentos.py    # gera o Parquet e o relatório
.venv/bin/python -m pytest                          # testes de normalização e da regra
```

Saídas (fora do git, em `data/processed/`):

- `atropelamentos.parquet`: a base. As ressalvas abaixo vão também nos metadados do
  arquivo (chave `ressalvas`).
- `atropelamentos_qualidade.json`: relatório de cobertura e diagnóstico da fonte,
  regenerado a cada execução.

## De onde vêm os dados

| Fonte (CKAN, licença ODbL) | Recurso | Uso |
|---|---|---|
| `acidentes-de-transito-com-e-sem-vitimas` | um CSV por ano, 2015–2024 | sinistros |
| `localizacao-dos-semaforos` | só **"Semáforos do Recife"** (712 semáforos) | lat/lon |

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
| `lat`, `lon` | float | do semáforo, ver abaixo |
| `coord_fonte` | texto | `"semaforo"` quando há coordenada, null caso contrário |
| `coord_confere` | bool | null sem coordenada; ver abaixo |
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

## Como as coordenadas são obtidas

Os sinistros não têm lat/lon. A única coordenada usada é a do semáforo informado em
`num_semaforo`: junção exata `num_semaforo_norm` = `semaforo_norm` (os dois lados sem zeros à
esquerda e sem `,0`). **Nenhum geocodificador externo é chamado.** Linhas sem par ficam com
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

## Cobertura encontrada (execução de 05/11/2026)

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

Os números atuais estão sempre em `atropelamentos_qualidade.json`; esta tabela é um retrato.

Leitura: a coordenada por semáforo cobre pouco e de forma enviesada — só cruzamentos
semaforizados, e quase nada em 2018, 2023 e 2024, quando `num_semaforo` foi pouco
preenchido (6%, 8,5% e 3,7% de todos os sinistros). Um mapa de risco feito só com as linhas
com coordenada mostra **onde há semáforo**, não onde há mais atropelamento. Para cobrir o
resto, a próxima etapa precisa geocodificar `endereco_norm` + `bairro` (fora do escopo da M1).

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
   coordenada é do semáforo informado no chamado, não do ponto exato; o vínculo é por número
   digitado e tem erro (ver `coord_confere`).
8. **Mudança de formulário** (docs/06 #9): `protocolo` só a partir de 2022; `num_semaforo` só a
   partir de 2018; contagens vazias até 2020 vs. `0` depois; vocabulário de `tipo` muda em
   2018 e 2021. Linhas com lixo no `tipo` (`NATUREZA`, `SANTO AMARO`, `0`...) não são
   atropelamento e não entram; horas inválidas (`CITTAMOBI`, `29208:00:00`...) viram null.
