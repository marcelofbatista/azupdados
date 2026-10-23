# azupdados

🇬🇧 **English** · 🇧🇷 [Português](README.pt-BR.md) · [![CI](https://github.com/marcelofbatista/azupdados/actions/workflows/ci.yml/badge.svg)](https://github.com/marcelofbatista/azupdados/actions/workflows/ci.yml)

**An open data warehouse of Brazilian basic education — School Census, SAEB, IDEB and IBGE as historical series, built with a medallion architecture, Kimball modelling and dbt.**

> Status: 🚧 under active development. The roadmap at the end of this file shows what is done. Nothing here describes as finished something that does not exist yet.

> Table and column names are in Portuguese, matching the official sources (INEP, Brazil's national education statistics agency). A short glossary is at the end.

---

## Why this project exists

INEP's education microdata are public, but using them well is hard. Layouts change from year to year, sentinel codes hide inside numeric columns, the grain of a dataset changes without notice, and seemingly simple indicators (enrolment coverage, age-grade distortion) depend on denominators that come from a different institution, IBGE (the national statistics office).

`azupdados` solves this once, in an auditable way: it keeps the official files exactly as published, harmonises the historical series, turns every pitfall it finds into an automated test, and delivers a dimensional model ready for analysis and BI.

> **What about Base dos Dados?** It already publishes cleaned INEP and IBGE data on BigQuery and is used here as a **cross-check reference**. `azupdados` has a different focus: its own dimensional model, explicit data-quality tests and indicators with documented denominators.

## Sources

| Source | Grain | Coverage | Status |
|---|---|---|---|
| School Census (INEP) — `microdados_ed_basica` | school × year | Brazil, 2014–2024 (2025 will be added when INEP publishes the microdata; as of Oct 2026 the page stops at 2024) | ✅ 2014–2024 reconciled with INEP (zero difference in every year) |
| IDEB — basic education development index (INEP) | school, municipality, state × edition | 2005–2025 | ✅ |
| Education indicators (INEP) — pass/fail/dropout rates, age-grade distortion, students per class, daily class hours, teacher qualification, workload and stability, school management complexity | school × year × grade level | Brazil, 2015–2025 | ✅ 2015–2025 on real data; pass + fail + dropout add up to 100% (±0.5 pp) in all 12.3M rows |
| INSE — school socioeconomic level (INEP) | school × SAEB edition | 2011–2013, 2015, 2019, 2021, 2023 | ✅ (pre-2019 methodologies flagged as not comparable) |
| SAEB (INEP) — national assessment microdata | student × edition | 2011–2023 | ⏳ |
| Population Censuses 2010 and 2022 (IBGE) | municipality × age × sex | Brazil | ⏳ |
| Population projections (IBGE, 2024 revision) | state × age × sex × year | 2000–2070 | ⏳ |
| Territories (IBGE) | region, state, municipality | Brazil | ⏳ |
| SEDAP+ (INEP) — special education by type of disability | state × administrative network × year | Brazil, 2015–2024 | ✅ loaded; validation against the official Synopsis in progress |

No personally identifiable information enters the repository or the database. Almost everything is open
data; the exception is **type of disability**, which INEP only releases through SEDAP+ (its protected-data
access service) with differential privacy. From it, `azupdados` uses only aggregates by state and
administrative network, and only as a *proportion*: the scale always comes from the open Census (see
pitfall 09). Raw API responses stay out of the repository.

## Architecture

```
 INEP / IBGE  ──►  BRONZE  ──────────────►  SILVER  ─────────────────►  GOLD
 (official        original file            typed, sentinels             Kimball: conformed dimensions
  file)           + md5 + Parquet          handled, layouts             + facts  ──►  indicator marts
                  + raw table (text)       harmonised across years
                                                                         ──►  Superset (public) · Power BI (PBIP)
 └─ Python ──────┘└──────────────── dbt (SQL + tests) ──────────────────┘
```

| Layer | What it is | Where |
|---|---|---|
| **Bronze** | Faithful copy of the official file, hash-checked, converted to Parquet and loaded into text-only tables | `ingest/` → schema `bronze` |
| **Silver** | Typing, column names standardised across years, sentinel codes handled | `dbt/azupdados/models/silver` |
| **Gold** | Dimensional model (Kimball): conformed `dim_*`, `fato_*` (fact) tables with a declared grain, and indicator marts | `dbt/azupdados/models/gold` |

**Why medallion *and* Kimball?** Medallion organises the data *lifecycle* (from raw to consumable); Kimball organises the *modelling* of the consumption layer. One answers "what stage is this data in?", the other "how should it be queried?".

**Why each tool:**

- **Python** for ingestion: download, md5 check, Parquet conversion, bulk load via `COPY`.
- **dbt** for transformations: versioned SQL, explicit dependencies, declarative tests and generated documentation.
- **PySpark** only for the student-level SAEB microdata, where the project's real volume is. Using Spark on school-level tables (hundreds of thousands of rows per year) would add complexity with no gain.
- **PostgreSQL** as the main warehouse; the gold layer is replicated to **BigQuery** for cloud consumption.

Conventions: surrogate keys `<table>_sk`; fact keys `<fact_name>_sk`; year is always `ano_censo`; every table and column documented in dbt.

## Documented pitfalls

The SEDAP+ table catalogue is in [`docs/fontes/sedap_catalogo.md`](docs/fontes/sedap_catalogo.md).

Every problem found in the data becomes three things: an automated test, a fix in silver and a note in [`docs/armadilhas/`](docs/armadilhas/) (Portuguese). The synthetic fixtures in [`data/fixtures/`](data/fixtures/) reproduce these pitfalls on purpose, and CI runs the full pipeline on them on every commit.

| # | Pitfall | Test | Status |
|---|---|---|---|
| 01 | Sentinel codes (88888, 99999, 77777) in `QT_*` columns summed as if they were counts | `sem_sentinela_inep` | ✅ |
| 02 | School Census layout changes between years (columns created, renamed and dropped) | macro `coluna_ou_nulo` | ✅ |
| 03 | SAEB datasets change grain between editions (assessed × enrolled students) | — | ⏳ |
| 04 | Duplicate rows in official extracts | `unique` on the natural key | 🚧 |
| 05 | A uniqueness test run only on non-null values hides duplicates | `unicidade_com_nulos` | ✅ |
| 06 | Integer counts exported as `"0.0"` break a direct cast to integer | macro `para_inteiro` | ✅ |
| 07 | "Number of schools" depends on the definition: in 2024 there are 215,545 rows in the file, 181,065 active and 179,286 with enrolments — INEP reports about 179.3 thousand | — | 🚧 |
| 08 | Missing values encoded differently: up to 2021, schools without enrolments have `0` in count columns; from 2022, null. Per-school averages change for that reason alone | — | 🚧 |
| 09 | SEDAP+ numbers carry differential-privacy noise (including negative values in small cells) and, unfiltered, count special-education support students twice (+30% to +53%) | `assert_sedap_total_proximo_do_censo_aberto` | 🚧 |
| 10 | IBGE and INEP swap the codes for *parda* and *amarela* (4/3 × 3/4): joining on the number inverts the groups | `unique` on both codes of `dim_cor_raca` | ✅ |
| 11 | IDEB spreadsheets: technical header after title rows, unnamed ID columns and a repeated column name (the 2025 pass-rate indicator is labelled 2023) | `unicidade_com_nulos` in silver | ✅ |
| 12 | INEP per-school indicators: the technical header sometimes lies — school code and name swapped (students per class 2016–2018) and column names shifted relative to the data (pass/fail rates 2018–2020). Bronze fixes it from the shape of the content; silver maps by the human-readable label, not by the column name | `assert_rendimento_soma_100`, `assert_ind_nome_diverge_do_rotulo` (audit) | ✅ |

## Reconciliation with official numbers

Every computed total is checked against the number published by INEP, recorded with its source in
[`seeds/ref_totais_oficiais_inep.csv`](dbt/azupdados/seeds/ref_totais_oficiais_inep.csv). The test
`assert_matriculas_batem_com_inep` requires an exact match.

| Year | Basic-education enrolments (INEP) | Computed in `azupdados` | Difference |
|---|---|---|---|
| 2014 | 49,771,371 | 49,771,371 | 0 |
| 2015 | 48,796,512 | 48,796,512 | 0 |
| 2016 | 48,817,479 | 48,817,479 | 0 |
| 2017 | 48,608,093 | 48,608,093 | 0 |
| 2018 | 48,455,867 | 48,455,867 | 0 |
| 2019 | 47,874,246 | 47,874,246 | 0 |
| 2020 | 47,295,294 | 47,295,294 | 0 |
| 2021 | 46,668,401 | 46,668,401 | 0 |
| 2022 | 47,382,074 | 47,382,074 | 0 |
| 2023 | 47,304,632 | 47,304,632 | 0 |
| 2024 | 47,088,922 | 47,088,922 | 0 |

### IDEB

| Stage | IDEB Brazil 2023 (INEP) | Computed in `azupdados` |
|---|---|---|
| Primary, years 1–5 | 6.0 | 6.0 |
| Lower secondary, years 6–9 | 5.0 | 5.0 |
| Upper secondary | 4.3 | 4.3 |

The test `assert_ideb_brasil_bate_com_inep` compares to one decimal place. It is what found the column
with no technical name in the 2025 spreadsheet (pitfall 11).

## How to run

```bash
git clone https://github.com/marcelofbatista/azupdados.git && cd azupdados
cp .env.example .env                      # set the password (full guide, in Portuguese: docs/setup_servidor.md)
make setup                                # venv + Python and dbt dependencies
make up                                   # PostgreSQL in Docker
make bronze-censo ARQ=data/landing/censo_escolar/microdados_ed_basica_2024.csv ANO=2024
make dbt-build                            # silver + gold + tests
```

## Stack

PostgreSQL 16 · Python 3.12 · dbt-core + dbt-postgres · PySpark (SAEB) · Docker Compose · GitHub Actions · BigQuery (gold replica) · Apache Superset · Power BI (PBIP)

## From a state-level DW to a national one

`azupdados` grew out of a state-level data warehouse on inclusive education. Every fact there that comes
from a public source gets a national version here; those that depend on a single network's internal
systems are left out.

| Topic | In `azupdados` | Source | Status |
|---|---|---|---|
| Enrolments by stage, special education and full-time schooling | `fato_matricula_escola_ano` | School Census | ✅ |
| Enrolments by race/colour, sex and age group | `fato_matricula_{cor_raca,sexo,faixa_etaria}_escola_ano` | School Census | ✅ |
| Special education by type of disability | `fato_ee_tipo_uf_ano` | SEDAP+ anchored to the Census | ✅ |
| School infrastructure | `fato_infraestrutura_escola_ano` | School Census | ✅ |
| Teachers and classes per school | `fato_docentes_turmas_escola_ano` | School Census | ✅ |
| Non-teaching staff (psychologist, sign-language interpreter...) | `fato_profissionais_escola_ano` | School Census | ✅ |
| Pass, fail and dropout rates by stage and grade | `fato_rendimento_escola_ano` | INEP pass/fail rates, 2015–2025 | ✅ |
| Age-grade distortion, students per class, class hours | `fato_{distorcao_idade_serie,alunos_turma,horas_aula}_escola_ano` | INEP education indicators, 2015–2025 | ✅ |
| Teacher qualification, workload and stability; management complexity | `fato_{formacao_docente,esforco_docente,regularidade_docente,complexidade_gestao}_escola_ano` | INEP education indicators, 2015–2025 | ✅ |
| School socioeconomic level | `fato_inse_escola_edicao` | INSE (INEP) | ✅ |
| IDEB | `fato_ideb_{escola,municipio,agregado}_ano` | IDEB (INEP), 2005–2025 series | ✅ |
| Proficiency | `fato_saeb_*` | SAEB, with PySpark | ⏳ |
| Population (denominator) | `fato_populacao_*` | IBGE | ⏳ |

Left out, because they are not public or belong to a single network: school management systems, state-run
censuses, internal forms and local household surveys.

## Roadmap

- [x] **v0.1 — Foundation**: medallion structure, Docker, bronze ingestion of the School Census with md5, first dbt models and tests, CI.
- [ ] **v0.2 — Historical series**: School Census 2014–2024 harmonised ✅, IDEB ✅, INEP indicators and INSE ✅, `dim_tempo` with pandemic phases and electoral-term cycles ✅; still to come: Census 2025 (waiting on INEP) and IBGE territories.
- [ ] **v0.3 — Population**: IBGE 2010/2022 censuses and projections as denominators; coverage marts.
- [ ] **v0.4 — Learning**: student-level SAEB with PySpark, aggregated by school and municipality.
- [ ] **v0.5 — Consumption**: gold on BigQuery, public Superset dashboard, Power BI dashboard versioned as PBIP.

## Glossary

| Term | Meaning |
|---|---|
| `fato_` / `dim_` | fact / dimension table |
| `escola`, `ano_censo`, `etapa` | school, census year, education stage/grade level |
| `matricula` | enrolment |
| `rendimento` (`aprovacao`, `reprovacao`, `abandono`) | pass / fail / dropout rates |
| `distorcao_idade_serie` | share of students two or more years older than expected for their grade |
| `dependencia_adm` | administrative network: federal, state, municipal, private |
| `tempo integral` | full-time schooling (7+ hours a day) |
| `armadilhas` | pitfalls |

## About the author

**Marcelo F Batista** — data scientist and engineer in the public sector, where he leads the build of an education observatory (PostgreSQL, dimensional modelling, BI). `azupdados` is a personal project, built exclusively on open data and independent of any institution.

Built with AI pair programming (Claude). Data modelling decisions, validation and every reconciliation are reviewed and run by the author.

## Licence

Code: MIT. The data belong to the original sources (INEP, IBGE) and follow each one's terms of use.
