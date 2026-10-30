"""SILVER do SAEB por aluno, com PySpark: as três edições harmonizadas num só formato longo.

Grão de saída: aluno × disciplina (LP, MT e, onde houver, CH e CN). Uma linha por aluno e disciplina avaliada
no arquivo, com presença, proficiência na escala SAEB, peso amostral e o perfil do aluno decodificado.

De-para do questionário, tirado do dicionário oficial de cada edição (make saeb-dicionario):
  cor/raça  2019: TX_RESP_Q002 (a–f)      2021 e 2023: TX_RESP_Q04 (A–F)
  sexo      2019: não há pergunta          2021: TX_RESP_Q01 (A, B)   2023: TX_RESP_Q01 (A, B, C)
  O 2º ano do fundamental (TS_ALUNO_2EF) não tem questionário: cor/raça e sexo ficam nulos.
Cor/raça sai no código do Censo Escolar (1 branca, 2 preta, 3 parda, 4 amarela, 5 indígena, 0 não declarada),
para casar com dim_cor_raca.codigo_educacenso. Sexo sai como 1 masculino, 2 feminino, 9 "não quero declarar".
Resposta em branco ou nula (".", "*") vira nulo: não respondeu é diferente de "não quis declarar".

INSE do aluno (2021 e 2023): o nível só vale quando IN_INSE = 1. Com IN_INSE = 0 o INEP grava nível 1, que não
é o piso da escala, é "não calculado" — por isso a silver anula o nível nesses casos.

ID_ESCOLA e ID_MUNICIPIO ficam só na bronze: no arquivo público do aluno eles não são o código real
(ver make saeb-verificar-escola), e mantê-los aqui convidaria a um join errado.

Uso:
  python spark/silver_saeb.py --anos 2019,2021,2023
"""

from __future__ import annotations

import argparse
from functools import reduce
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from sessao import criar_sessao

BRONZE = "data/bronze/saeb/ts_aluno"
SILVER = "data/silver/saeb/aluno_disciplina"
ARQUIVOS = ["2EF", "5EF", "9EF", "34EM"]
DISCIPLINAS = ["LP", "MT", "CH", "CN"]

PERGUNTA_COR = {2019: "tx_resp_q002", 2021: "tx_resp_q04", 2023: "tx_resp_q04"}
PERGUNTA_SEXO = {2021: "tx_resp_q01", 2023: "tx_resp_q01"}
COR_PARA_CENSO = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 0}
SEXO_PARA_CODIGO = {"A": 1, "B": 2, "C": 9}


def col(df: DataFrame, nome: str):
    return F.col(nome) if nome in df.columns else F.lit(None).cast("string")


def inteiro(df: DataFrame, nome: str):
    return F.trim(col(df, nome)).cast("int")


def decimal(df: DataFrame, nome: str):
    """Números do INEP podem vir com vírgula decimal; vazio vira nulo."""
    return F.regexp_replace(F.trim(col(df, nome)), ",", ".").cast("double")


def decodificar(df: DataFrame, nome: str | None, mapa: dict[str, int]):
    if not nome or nome not in df.columns:
        return F.lit(None).cast("int")
    resposta = F.upper(F.trim(F.col(nome)))
    expr = None
    for letra, codigo in mapa.items():
        expr = (F.when(resposta == letra, F.lit(codigo)) if expr is None
                else expr.when(resposta == letra, F.lit(codigo)))
    return expr.otherwise(F.lit(None)).cast("int")


def harmonizar(df: DataFrame, ano: int, arquivo: str) -> DataFrame | None:
    disciplinas = [d for d in DISCIPLINAS if f"peso_aluno_{d.lower()}" in df.columns]
    if not disciplinas:
        return None
    in_inse = inteiro(df, "in_inse")
    comuns = [
        F.lit(ano).alias("ano"), F.lit(arquivo).alias("arquivo"),
        inteiro(df, "id_serie").alias("id_serie"),
        inteiro(df, "id_regiao").alias("id_regiao"), inteiro(df, "id_uf").alias("id_uf"),
        inteiro(df, "id_area").alias("id_area"), inteiro(df, "in_publica").alias("in_publica"),
        inteiro(df, "id_localizacao").alias("id_localizacao"),
        inteiro(df, "in_situacao_censo").alias("in_situacao_censo"),
        inteiro(df, "in_amostra").alias("in_amostra"), col(df, "estrato").alias("estrato"),
        col(df, "id_aluno").alias("id_aluno"),
        decodificar(df, PERGUNTA_COR.get(ano), COR_PARA_CENSO).alias("cor_raca_censo"),
        decodificar(df, PERGUNTA_SEXO.get(ano), SEXO_PARA_CODIGO).alias("sexo_codigo"),
        in_inse.alias("in_inse"),
        F.when(in_inse == 1, decimal(df, "inse_aluno")).alias("inse_aluno"),
        F.when(in_inse == 1, inteiro(df, "nu_tipo_nivel_inse")).alias("nivel_inse"),
        F.when(in_inse == 1, decimal(df, "peso_aluno_inse")).alias("peso_aluno_inse"),
    ]
    partes = []
    for d in disciplinas:
        s = d.lower()
        partes.append(df.select(
            *comuns, F.lit(d).alias("disciplina"),
            inteiro(df, f"in_presenca_{s}").alias("in_presenca"),
            inteiro(df, f"in_proficiencia_{s}").alias("in_proficiencia"),
            decimal(df, f"peso_aluno_{s}").alias("peso_aluno"),
            decimal(df, f"proficiencia_{s}_saeb").alias("proficiencia_saeb"),
            decimal(df, f"erro_padrao_{s}_saeb").alias("erro_padrao_saeb"),
        ))
    return reduce(DataFrame.unionByName, partes)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", required=True)
    args = p.parse_args()

    spark = criar_sessao("silver-saeb")
    try:
        for ano in [int(a) for a in args.anos.split(",")]:
            partes = []
            for arquivo in ARQUIVOS:
                caminho = Path(BRONZE) / f"ano={ano}" / f"arquivo={arquivo}"
                if not caminho.exists():
                    print(f"[{ano} {arquivo}] sem bronze, pulando")
                    continue
                bruto = spark.read.parquet(str(caminho))
                h = harmonizar(bruto, ano, arquivo)
                if h is not None:
                    partes.append(h)
            if not partes:
                continue
            silver = reduce(DataFrame.unionByName, partes)
            destino = f"{SILVER}/ano={ano}"
            silver.drop("ano").write.mode("overwrite").partitionBy("arquivo").parquet(destino)

            r = (spark.read.parquet(destino).groupBy("arquivo", "disciplina")
                 .agg(F.count(F.lit(1)).alias("linhas"),
                      F.avg(F.col("proficiencia_saeb").isNotNull().cast("int")).alias("com_prof"),
                      F.avg(F.col("cor_raca_censo").isNotNull().cast("int")).alias("com_cor"),
                      F.avg(F.col("sexo_codigo").isNotNull().cast("int")).alias("com_sexo"),
                      F.avg(F.col("nivel_inse").isNotNull().cast("int")).alias("com_inse"))
                 .orderBy("arquivo", "disciplina").collect())
            print(f"\n[{ano}] silver gravada em {destino}")
            for x in r:
                print(f"  {x['arquivo']:<5}{x['disciplina']:<3}{x['linhas']:>11,} linhas · com proficiência "
                      f"{x['com_prof']:.1%} · cor/raça {x['com_cor']:.1%} · sexo {x['com_sexo']:.1%} · "
                      f"INSE {x['com_inse']:.1%}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
