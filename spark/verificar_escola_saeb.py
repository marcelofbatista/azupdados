"""O ID_ESCOLA do SAEB por aluno é o código real da escola? Verificação contra o Censo Escolar.

Ter 8 dígitos não basta: um código embaralhado também tem 8 dígitos. O teste aqui é duplo, por ano e arquivo:
  - casa_escola:    % de alunos cujo ID_ESCOLA existe em gold.dim_escola (co_entidade do Censo);
  - casa_municipio: % de alunos cujo ID_ESCOLA existe E cujo ID_MUNICIPIO é o município dessa escola no Censo.

Se o código fosse real, os dois ficariam perto de 100%. Se for embaralhado, o primeiro pode até dar alto por
coincidência (há ~180 mil códigos de escola), mas o segundo despenca, porque o embaralhamento não preserva o
par escola–município.

Uso (depois de `make saeb-bronze`):
  python spark/verificar_escola_saeb.py
"""

from __future__ import annotations

import os

import psycopg
from pyspark.sql import functions as F
from sessao import criar_sessao

BRONZE = "data/bronze/saeb/ts_aluno"


def escolas_do_censo() -> list[tuple[str, str]]:
    conninfo = (
        f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )
    with psycopg.connect(conninfo) as conn:
        return conn.execute(
            "select distinct co_entidade::text, co_municipio::text from gold.dim_escola where co_entidade is not null"
        ).fetchall()


def main() -> None:
    spark = criar_sessao("verificar-escola-saeb")
    try:
        censo = spark.createDataFrame(escolas_do_censo(), "co_entidade string, co_municipio_censo string")
        print(f"Escolas no Censo (gold.dim_escola): {censo.count():,}")
        alunos = spark.read.parquet(BRONZE).select("ano", "arquivo", "id_escola", "id_municipio")
        r = (
            alunos.join(F.broadcast(censo), alunos.id_escola == censo.co_entidade, "left")
            .groupBy("ano", "arquivo")
            .agg(
                F.count(F.lit(1)).alias("alunos"),
                F.avg(F.col("co_entidade").isNotNull().cast("int")).alias("casa_escola"),
                F.avg(F.coalesce(F.col("co_municipio_censo") == F.col("id_municipio"), F.lit(False)).cast("int"))
                .alias("casa_municipio"),
            )
            .orderBy("ano", "arquivo")
            .collect()
        )
        print(f"\n{'ano':<6}{'arquivo':<9}{'alunos':>12}{'casa_escola':>14}{'casa_municipio':>16}")
        for x in r:
            print(f"{x['ano']:<6}{x['arquivo']:<9}{x['alunos']:>12,}{x['casa_escola']:>14.1%}{x['casa_municipio']:>16.1%}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
