"""Agregação do SAEB por aluno (PySpark) e carga no Postgres, para a camada gold em dbt.

Por que agregar no Spark: são ~20 milhões de linhas aluno × disciplina por edição. O Postgres do projeto não
precisa guardá-las para responder às perguntas da gold; precisa das somas certas.

Grão da saída (tabela silver.saeb_agregado):
  ano × arquivo × série × UF × rede (pública/privada) × localização × área (capital/interior) ×
  disciplina × cor/raça × sexo × nível INSE × situação no Censo

Medidas ADITIVAS, para que qualquer recorte da gold (só UF, só rede, Brasil inteiro...) seja uma soma exata:
  n_alunos             linhas do arquivo (todos os alunos esperados)
  n_presentes          IN_PRESENCA = 1
  n_com_proficiencia   proficiência SAEB preenchida
  soma_peso            Σ peso, só de quem tem proficiência
  soma_peso_prof       Σ peso × proficiência
  soma_peso_prof2      Σ peso × proficiência²  (permite o desvio-padrão ponderado)
Média ponderada de qualquer recorte = Σ soma_peso_prof / Σ soma_peso. Média simples de médias não é usada
em lugar nenhum: daria peso igual a uma UF pequena e a uma grande.

Uso:
  python spark/agregar_saeb.py --anos 2019,2021,2023
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
from pyspark.sql import functions as F
from sessao import criar_sessao

SILVER = "data/silver/saeb/aluno_disciplina"
TABELA = "silver.saeb_agregado"
CHAVES = ["ano", "arquivo", "id_serie", "id_uf", "in_publica", "id_localizacao", "id_area", "disciplina",
          "cor_raca_censo", "sexo_codigo", "nivel_inse", "in_situacao_censo"]
MEDIDAS = ["n_alunos", "n_presentes", "n_com_proficiencia", "soma_peso", "soma_peso_prof", "soma_peso_prof2"]

DDL = Path("sql/init/02_saeb.sql").read_text()  # mesma definição usada no CI e na criação do banco


def conninfo() -> str:
    return (f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} port={os.environ.get('POSTGRES_PORT', '5432')} "
            f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
            f"password={os.environ['POSTGRES_PASSWORD']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", required=True)
    args = p.parse_args()
    anos = [int(a) for a in args.anos.split(",")]

    spark = criar_sessao("agregar-saeb")
    try:
        alunos = spark.read.parquet(SILVER).where(F.col("ano").isin(anos))
        tem_prof = F.col("proficiencia_saeb").isNotNull() & F.col("peso_aluno").isNotNull()
        peso = F.when(tem_prof, F.col("peso_aluno"))
        agregado = alunos.groupBy(*CHAVES).agg(
            F.count(F.lit(1)).alias("n_alunos"),
            # presença ausente no arquivo (coluna nula no grupo inteiro) conta como 0, não como nulo
            F.sum(F.coalesce((F.col("in_presenca") == 1).cast("int"), F.lit(0))).alias("n_presentes"),
            F.sum(F.col("proficiencia_saeb").isNotNull().cast("int")).alias("n_com_proficiencia"),
            F.sum(peso).alias("soma_peso"),
            F.sum(peso * F.col("proficiencia_saeb")).alias("soma_peso_prof"),
            F.sum(peso * F.col("proficiencia_saeb") * F.col("proficiencia_saeb")).alias("soma_peso_prof2"),
        )
        linhas = [tuple(r[c] for c in CHAVES + MEDIDAS) for r in agregado.toLocalIterator()]
        print(f"Agregado: {len(linhas):,} linhas para {anos}")

        with psycopg.connect(conninfo()) as conn, conn.cursor() as cur:
            cur.execute(DDL)
            cur.execute(f"delete from {TABELA} where ano = any(%s)", (anos,))
            with cur.copy(f"copy {TABELA} ({', '.join(CHAVES + MEDIDAS)}) from stdin") as cp:
                for linha in linhas:
                    cp.write_row(linha)
            cur.execute(
                f"""select ano, arquivo, disciplina, sum(n_alunos), sum(n_com_proficiencia),
                           round((sum(soma_peso_prof) / nullif(sum(soma_peso), 0))::numeric, 1)
                    from {TABELA} where ano = any(%s) group by 1, 2, 3 order by 1, 2, 3""", (anos,))
            print(f"\n{'ano':<6}{'arquivo':<9}{'disc':<6}{'alunos':>12}{'com nota':>12}{'média Brasil':>14}")
            for a, arq, d, n, np_, m in cur.fetchall():
                print(f"{a:<6}{arq:<9}{d:<6}{n:>12,}{np_:>12,}{m if m is not None else '—':>14}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
