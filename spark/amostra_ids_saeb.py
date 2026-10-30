"""Diagnóstico rápido: como são os ID_ESCOLA e ID_MUNICIPIO do SAEB comparados aos códigos reais do Censo.

Mostra faixa (mínimo, máximo), primeiro dígito mais comum e quantos municípios do SAEB existem na lista do
IBGE. Serve para documentar o mascaramento com números, não só com "não casou".
"""

from __future__ import annotations

import os

import psycopg
from pyspark.sql import functions as F
from sessao import criar_sessao


def main() -> None:
    conninfo = (f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} port={os.environ.get('POSTGRES_PORT', '5432')} "
                f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
                f"password={os.environ['POSTGRES_PASSWORD']}")
    with psycopg.connect(conninfo) as conn:
        e = conn.execute("select min(co_entidade::bigint), max(co_entidade::bigint) from gold.dim_escola").fetchone()
        mun = [r[0] for r in conn.execute("select distinct co_municipio::text from gold.dim_escola").fetchall()]
    print(f"Censo   co_entidade: {e[0]} … {e[1]}   municípios distintos: {len(mun):,}")

    spark = criar_sessao("amostra-ids-saeb")
    try:
        df = spark.read.parquet("data/bronze/saeb/ts_aluno").where("arquivo = '5EF'")
        municipios = spark.createDataFrame([(m,) for m in mun], "co_municipio string")
        for x in df.groupBy("ano").agg(
            F.min(F.col("id_escola").cast("bigint")).alias("min_esc"),
            F.max(F.col("id_escola").cast("bigint")).alias("max_esc"),
            F.countDistinct("id_escola").alias("escolas"),
            F.countDistinct("id_municipio").alias("municipios"),
        ).orderBy("ano").collect():
            print(f"SAEB {x['ano']} 5EF  id_escola: {x['min_esc']} … {x['max_esc']}  "
                  f"escolas distintas: {x['escolas']:,}  municípios distintos: {x['municipios']:,}")
        mun_saeb = df.select("ano", "id_municipio").distinct()
        r = (mun_saeb.join(municipios, mun_saeb.id_municipio == municipios.co_municipio, "left")
             .groupBy("ano").agg(F.avg(F.col("co_municipio").isNotNull().cast("int")).alias("existe"))
             .orderBy("ano").collect())
        for x in r:
            print(f"SAEB {x['ano']}  municípios do SAEB que existem no Censo: {x['existe']:.1%}")
        print("\nAmostra (ano, UF, município, escola):")
        for x in df.select("ano", "id_uf", "id_municipio", "id_escola").limit(5).collect():
            print("  ", x["ano"], x["id_uf"], x["id_municipio"], x["id_escola"])
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
