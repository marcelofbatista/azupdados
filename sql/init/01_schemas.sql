-- Camadas do medalhão. Executado só na primeira criação do volume.
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS meta;

-- Registro de cada arquivo oficial carregado (linhagem da bronze).
CREATE TABLE IF NOT EXISTS meta.carga_arquivo (
    carga_arquivo_sk  BIGSERIAL PRIMARY KEY,
    fonte             TEXT        NOT NULL,   -- ex.: inep_censo_escolar
    ano_referencia    INT         NOT NULL,
    arquivo           TEXT        NOT NULL,
    md5               CHAR(32)    NOT NULL,
    md5_oficial_ok    BOOLEAN,                -- NULL quando o INEP não publica md5
    tabela_destino    TEXT        NOT NULL,
    linhas            BIGINT,
    colunas           INT,
    carregado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fonte, ano_referencia, md5)
);
