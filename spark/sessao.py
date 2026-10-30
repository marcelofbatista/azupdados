"""Sessão Spark local do azupdados.

O servidor de staging tem 2 núcleos e ~11 GB de RAM. O Spark roda em modo local (um processo, sem cluster):
o ganho aqui não é distribuir entre máquinas, e sim ler CSVs de 1 GB sem estourar a memória, com leitura
colunar em Parquet e agregações que não cabem num pandas.

Ajustes por variável de ambiente: SPARK_DRIVER_MEMORY (padrão 6g), SPARK_LOCAL_DIRS (padrão data/spark_tmp).
"""

from __future__ import annotations

import os
from pathlib import Path

from pyspark.sql import SparkSession


def criar_sessao(nome: str) -> SparkSession:
    tmp = Path(os.environ.get("SPARK_LOCAL_DIRS", "data/spark_tmp")).resolve()
    tmp.mkdir(parents=True, exist_ok=True)
    spark = (
        SparkSession.builder.appName(f"azupdados-{nome}")
        .master(os.environ.get("SPARK_MASTER", "local[*]"))
        .config("spark.driver.memory", os.environ.get("SPARK_DRIVER_MEMORY", "6g"))
        .config("spark.local.dir", str(tmp))
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.parquet.compression.codec", "zstd")
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark
