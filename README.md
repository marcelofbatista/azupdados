# azupdados

**Data warehouse aberto da educação básica brasileira — Censo Escolar, SAEB, IDEB e IBGE em série histórica, com arquitetura medalhão, modelagem Kimball e transformações em dbt.**

> Status: 🚧 em construção ativa. O roadmap no fim deste arquivo mostra o que já está pronto. Nada aqui descreve como pronto algo que ainda não existe.

---

## Por que este projeto existe

Os microdados educacionais do INEP são públicos, mas usá-los bem é difícil. Os layouts mudam de ano para ano, há códigos-sentinela escondidos em colunas numéricas, o grão das bases muda sem aviso e indicadores aparentemente simples (taxa de atendimento, distorção idade-série) dependem de denominadores que vêm de outra instituição, o IBGE.

O `azupdados` resolve isso uma vez, de forma auditável: preserva os arquivos oficiais como vieram, harmoniza a série histórica, transforma cada armadilha encontrada em teste automatizado e entrega um modelo dimensional pronto para análise e BI.

> **E a Base dos Dados?** Ela já publica INEP e IBGE tratados no BigQuery e é usada aqui como **referência de conferência**. O foco do `azupdados` é outro: modelo dimensional próprio, testes de qualidade explícitos e indicadores com denominador documentado.

## Fontes

| Fonte | Grão | Cobertura | Status |
|---|---|---|---|
| Censo Escolar (INEP) — `microdados_ed_basica` | escola × ano | Brasil, 2014–2025 | 🚧 em andamento |
| IDEB (INEP) | escola, município, UF × edição | 2005–2025 | ⏳ |
| SAEB (INEP) — microdados | aluno × edição | 2011–2023 | ⏳ |
| Censos Demográficos 2010 e 2022 (IBGE) | município × idade × sexo | Brasil | ⏳ |
| Projeções de população (IBGE, revisão 2024) | UF × idade × sexo × ano | 2000–2070 | ⏳ |
| Territórios (IBGE) | região, UF, município | Brasil | ⏳ |

Somente dado aberto. Nenhuma informação pessoal identificável entra no repositório ou no banco.

## Arquitetura

```
 INEP / IBGE  ──►  BRONZE  ──────────────►  SILVER  ─────────────────►  GOLD
 (arquivo         arquivo original         tipado, sentinelas           Kimball: dimensões conformadas
  oficial)        + md5 + Parquet          tratados, layouts            + fatos  ──►  marts de indicadores
                  + tabela bruta (texto)   harmonizados entre anos
                                                                         ──►  Superset (público) · Power BI (PBIP)
 └─ Python ──────┘└──────────────── dbt (SQL + testes) ─────────────────┘
```

| Camada | O que é | Onde |
|---|---|---|
| **Bronze** | Cópia fiel do arquivo oficial, com hash conferido, convertida para Parquet e carregada em tabelas só-texto | `ingest/` → schema `bronze` |
| **Silver** | Tipagem, padronização de nomes entre anos, tratamento de códigos-sentinela | `dbt/azupdados/models/silver` |
| **Gold** | Modelo dimensional (Kimball): `dim_*` conformadas, `fato_*` com grão declarado, e marts de indicadores | `dbt/azupdados/models/gold` |

**Por que medalhão *e* Kimball?** O medalhão organiza o *ciclo de vida* do dado (do bruto ao consumível); o Kimball organiza a *modelagem* da camada de consumo. Um responde "em que estágio está este dado?", o outro responde "como ele deve ser consultado?".

**Por que cada ferramenta:**

- **Python** na ingestão: download, conferência de md5, conversão para Parquet, carga em massa via `COPY`.
- **dbt** nas transformações: SQL versionado, dependências explícitas, testes declarativos e documentação gerada.
- **PySpark** apenas nos microdados do SAEB por aluno, onde está o volume real do projeto. Usar Spark nas tabelas de escola (centenas de milhares de linhas por ano) seria complexidade sem ganho.
- **PostgreSQL** como warehouse principal; a camada gold é replicada no **BigQuery** para consumo em nuvem.

Convenções: chaves substitutas `<tabela>_sk`; chave de fato `<nome_do_fato>_sk`; ano sempre `ano_censo`; toda tabela e coluna documentada no dbt.

## Armadilhas documentadas

Cada problema encontrado nos dados vira três coisas: um teste automatizado, uma correção na silver e uma nota em [`docs/armadilhas/`](docs/armadilhas/). As fixtures sintéticas em [`data/fixtures/`](data/fixtures/) reproduzem essas armadilhas de propósito, e o CI roda o pipeline completo sobre elas a cada commit.

| # | Armadilha | Teste | Status |
|---|---|---|---|
| 01 | Códigos-sentinela (88888, 99999, 77777) em colunas `QT_*` somados como se fossem contagens | `sem_sentinela_inep` | ✅ |
| 02 | Layout do Censo Escolar muda entre anos (colunas criadas, renomeadas e extintas) | macro `coluna_ou_nulo` | ✅ |
| 03 | Bases do SAEB mudam de grão entre edições (avaliados × matriculados) | — | ⏳ |
| 04 | Linhas duplicadas em extratos oficiais | `unique` na chave natural | 🚧 |
| 05 | Teste de unicidade só sobre valores preenchidos esconde duplicatas | `unicidade_com_nulos` | ✅ |
| 06 | Contagem inteira exportada como `"0.0"` quebra o cast direto para inteiro | macro `para_inteiro` | ✅ |
| 07 | "Número de escolas" depende da definição: em 2024 há 215.545 linhas no arquivo, 181.065 em atividade e 179.286 com matrícula — o INEP divulga cerca de 179,3 mil | — | 🚧 |
| 08 | Ausência codificada de formas diferentes: até 2021, escolas sem matrícula vêm com `0` nas colunas de quantidade; a partir de 2022, vêm com nulo. Médias por escola mudam de valor só por isso | — | 🚧 |

## Reconciliação com números oficiais

Todo total calculado é conferido contra o número publicado pelo INEP, registrado com a fonte em
[`seeds/ref_totais_oficiais_inep.csv`](dbt/azupdados/seeds/ref_totais_oficiais_inep.csv). O teste
`assert_matriculas_batem_com_inep` exige igualdade exata.

| Ano | Matrículas na educação básica (INEP) | Calculado no `azupdados` | Diferença |
|---|---|---|---|
| 2015 | a conferir | 48.796.512 | — |
| 2016 | a conferir | 48.817.479 | — |
| 2017 | a conferir | 48.608.093 | — |
| 2018 | 48.455.867 | 48.455.867 | 0 |
| 2019 | 47.874.246 | 47.874.246 | 0 |
| 2020 | 47.295.294 | 47.295.294 | 0 |
| 2021 | 46.668.401 | 46.668.401 | 0 |
| 2022 | 47.382.074 | 47.382.074 | 0 |
| 2023 | 47.304.632 | 47.304.632 | 0 |
| 2024 | 47.088.922 | 47.088.922 | 0 |

## Como rodar

```bash
git clone https://github.com/marcelofbatista/azupdados.git && cd azupdados
cp .env.example .env                      # ajuste a senha (guia completo: docs/setup_servidor.md)
make setup                                # venv + dependências Python e dbt
make up                                   # PostgreSQL em Docker
make bronze-censo ARQ=data/landing/censo_escolar/microdados_ed_basica_2024.csv ANO=2024
make dbt-build                            # silver + gold + testes
```

## Stack

PostgreSQL 16 · Python 3.12 · dbt-core + dbt-postgres · PySpark (SAEB) · Docker Compose · GitHub Actions · BigQuery (réplica da gold) · Apache Superset · Power BI (PBIP)

## Roadmap

- [ ] **v0.1 — Fundação**: estrutura medalhão, Docker, ingestão bronze do Censo Escolar com md5, primeiros modelos e testes dbt, CI.
- [ ] **v0.2 — Série histórica**: Censo Escolar 2014–2025 harmonizado, territórios IBGE, IDEB.
- [ ] **v0.3 — População**: Censos 2010/2022 e projeções do IBGE como denominador; marts de atendimento.
- [ ] **v0.4 — Aprendizagem**: SAEB por aluno com PySpark, agregados por escola e município.
- [ ] **v0.5 — Consumo**: gold no BigQuery, painel público no Superset, painel Power BI versionado em PBIP.

## Sobre o autor

**Marcelo Batista** — cientista e engenheiro de dados no setor público, onde lidera a construção de um observatório educacional (PostgreSQL, modelagem dimensional, BI). O `azupdados` é um projeto pessoal, construído exclusivamente com dados abertos e independente de qualquer instituição.

## Licença

Código: MIT. Os dados pertencem às fontes originais (INEP, IBGE) e seguem os termos de uso de cada uma.
