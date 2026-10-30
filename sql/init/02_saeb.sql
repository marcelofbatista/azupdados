-- SAEB. Tabelas que NÃO são criadas pelo dbt: alimentadas por scripts (PySpark e leitor das planilhas oficiais).
-- Idempotente: roda na criação do volume, no CI e também é executado por spark/agregar_saeb.py.

-- Agregado aditivo do SAEB por aluno, produzido pelo PySpark a partir da silver em Parquet.
CREATE TABLE IF NOT EXISTS silver.saeb_agregado (
    ano                int  NOT NULL,
    arquivo            text NOT NULL,   -- 2EF, 5EF, 9EF, 34EM (arquivo TS_ALUNO_* de origem)
    id_serie           int,             -- código de série do INEP (2, 5, 9, 12, 13...)
    id_uf              int,
    in_publica         int,             -- 1 pública, 0 privada
    id_localizacao     int,             -- 1 urbana, 2 rural
    id_area            int,             -- 1 capital, 2 interior
    disciplina         text NOT NULL,   -- LP, MT, CH, CN
    cor_raca_censo     int,             -- código do Censo Escolar; nulo = não respondeu / sem questionário
    sexo_codigo        int,             -- 1 masculino, 2 feminino, 9 não quis declarar; nulo = não respondeu
    nivel_inse         int,             -- 1–8, só quando IN_INSE = 1 (2021+)
    in_situacao_censo  int,
    n_alunos           bigint NOT NULL,
    n_presentes        bigint NOT NULL,
    n_com_proficiencia bigint NOT NULL,
    soma_peso          double precision,
    soma_peso_prof     double precision,
    soma_peso_prof2    double precision,
    carregado_em       timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE silver.saeb_agregado IS
  'SAEB por aluno agregado pelo PySpark (spark/agregar_saeb.py) a partir da silver em Parquet. Medidas aditivas.';

-- Médias oficiais publicadas pelo INEP nas planilhas de resultados (TS_BRASIL, TS_UF), formato longo, como vieram.
CREATE TABLE IF NOT EXISTS bronze.saeb_resultado_oficial (
    ano              text,
    abrangencia      text,   -- BRASIL | UF
    co_uf            text,
    dependencia_adm  text,
    localizacao      text,
    capital          text,
    coluna           text,   -- ex.: MEDIA_5_LP
    valor            text,
    arquivo          text
);
