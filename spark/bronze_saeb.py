"""BRONZE do SAEB por aluno, com PySpark: CSV oficial → Parquet, sem transformar nenhum valor.

Para cada edição, o script:
  1. extrai do zip UM arquivo TS_ALUNO_* de cada vez (2EF, 5EF, 9EF, 34EM) para uma pasta temporária;
  2. calcula o md5 do CSV extraído;
  3. lê com Spark (separador ';', todas as colunas como texto — a tipagem é papel da silver);
  4. grava Parquet particionado em data/bronze/saeb/ts_aluno/ano=<ano>/arquivo=<etapa>/;
  5. apaga o CSV temporário (o zip original continua na landing) e registra a carga em meta.carga_arquivo;
  6. imprime um perfil rápido: linhas, UFs, alunos com proficiência e se ID_ESCOLA tem cara de código INEP.

O passo 6 existe para confirmar, na base nacional, o que vimos no DF: o arquivo público do aluno mascara a
escola e o município (LGPD). Se ID_ESCOLA não tiver 8 dígitos nem casar com o Censo, a gold não pode ser
por escola.

Uso:
  python spark/bronze_saeb.py --anos 2019,2021,2023
  python spark/bronze_saeb.py --anos 2019 --arquivos 5EF      # um só, para testar
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from pyspark.sql import functions as F
from sessao import criar_sessao

LANDING = Path("data/landing/saeb")
BRONZE = Path("data/bronze/saeb/ts_aluno")
TMP = Path("data/landing/saeb/_tmp")
FONTE = "inep_saeb_aluno"
ARQUIVOS = ["2EF", "5EF", "9EF", "34EM"]
PADRAO = re.compile(r"TS_ALUNO_(2EF|5EF|9EF|34EM)\.csv$", re.IGNORECASE)


def zips_da_edicao(ano: int) -> list[Path]:
    """Zips da edição registrados no manifesto (ignora educação infantil: não tem prova de aluno)."""
    manifesto = LANDING / "_manifesto.csv"
    if not manifesto.exists():
        sys.exit(f"Falta {manifesto}. Rode `make saeb-baixar` antes.")
    with manifesto.open() as f:
        zips = [Path(r["arquivo"]) for r in csv.DictReader(f) if int(r["ano"]) == ano]
    return [z for z in zips if "infantil" not in z.name.lower()]


def md5_arquivo(caminho: Path) -> str:
    h = hashlib.md5()
    with caminho.open("rb") as f:
        while bloco := f.read(1 << 24):
            h.update(bloco)
    return h.hexdigest()


def registrar_carga(ano: int, arquivo: str, md5: str, destino: str, linhas: int, colunas: int) -> None:
    """Linhagem em meta.carga_arquivo, como nas demais fontes. Sem .env carregado, só avisa."""
    if "POSTGRES_DB" not in os.environ:
        print("      (POSTGRES_* não definido: carga não registrada em meta.carga_arquivo)")
        return
    import psycopg

    conninfo = (
        f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )
    with psycopg.connect(conninfo) as conn:
        conn.execute(
            """INSERT INTO meta.carga_arquivo
                   (fonte, ano_referencia, arquivo, md5, md5_oficial_ok, tabela_destino, linhas, colunas)
               VALUES (%s, %s, %s, %s, NULL, %s, %s, %s)
               ON CONFLICT (fonte, ano_referencia, md5) DO UPDATE
                  SET linhas = EXCLUDED.linhas, colunas = EXCLUDED.colunas, carregado_em = now()""",
            (FONTE, ano, arquivo, md5, destino, linhas, colunas),
        )


def perfil(df, rotulo: str) -> None:
    """Perfil rápido em uma passada só sobre o Parquet recém-gravado."""
    tem = [c for c in ("proficiencia_lp_saeb", "proficiencia_mt_saeb") if c in df.columns]
    exprs = [
        F.count(F.lit(1)).alias("linhas"),
        F.countDistinct("id_uf").alias("ufs"),
        F.avg(F.col("id_escola").rlike(r"^\d{8}$").cast("int")).alias("escola_8dig"),
        F.avg(F.col("id_municipio").rlike(r"^\d{7}$").cast("int")).alias("municipio_7dig"),
    ]
    # o Spark lê campo vazio como nulo; coalesce para contar vazio como "sem proficiência", não ignorar
    exprs += [F.avg((F.coalesce(F.trim(F.col(c)), F.lit("")) != "").cast("int")).alias(f"com_{c[13:15]}")
              for c in tem]
    r = df.agg(*exprs).first().asDict()
    extras = "  ".join(f"{k}={v:.1%}" for k, v in r.items() if k.startswith("com_"))
    print(f"      perfil {rotulo}: {r['linhas']:,} linhas · {r['ufs']} UFs · "
          f"ID_ESCOLA com 8 dígitos={r['escola_8dig']:.1%} · ID_MUNICIPIO com 7 dígitos={r['municipio_7dig']:.1%} · "
          f"{extras}")


def processar(spark, ano: int, filtro: set[str] | None, manifesto: list[dict]) -> None:
    for zp in zips_da_edicao(ano):
        with zipfile.ZipFile(zp) as z:
            membros = [(m, PADRAO.search(m.filename)) for m in z.infolist()]
            for info, achado in [(m, a) for m, a in membros if a]:
                etapa = achado.group(1).upper()
                if filtro and etapa not in filtro:
                    continue
                print(f"\n[{ano} {etapa}] {zp.name} :: {info.filename} ({info.file_size / 1e6:.0f} MB)")
                TMP.mkdir(parents=True, exist_ok=True)
                csv_tmp = TMP / f"saeb_{ano}_{etapa}.csv"
                with z.open(info) as origem, csv_tmp.open("wb") as saida:
                    shutil.copyfileobj(origem, saida, 1 << 24)
                md5 = md5_arquivo(csv_tmp)
                print(f"      md5={md5}")

                df = (spark.read.option("header", True).option("sep", ";").option("inferSchema", False)
                      .option("encoding", "UTF-8").csv(str(csv_tmp.resolve())))
                df = df.toDF(*[c.strip().lower() for c in df.columns])
                destino = BRONZE / f"ano={ano}" / f"arquivo={etapa}"
                df.write.mode("overwrite").parquet(str(destino.resolve()))

                gravado = spark.read.parquet(str(destino.resolve()))
                linhas = gravado.count()
                perfil(gravado, f"{ano} {etapa}")
                csv_tmp.unlink()
                registrar_carga(ano, info.filename, md5, str(destino), linhas, len(df.columns))
                manifesto.append({"ano": ano, "arquivo": etapa, "origem": f"{zp.name}::{info.filename}",
                                  "md5_csv": md5, "linhas": linhas, "colunas": len(df.columns),
                                  "destino": str(destino), "registrado_em": datetime.now(UTC).isoformat()})


def gravar_manifesto(novas: list[dict]) -> None:
    caminho = BRONZE.parent / "_cargas_ts_aluno.csv"
    antigas = {}
    if caminho.exists():
        with caminho.open() as f:
            antigas = {(r["ano"], r["arquivo"]): r for r in csv.DictReader(f)}
    for r in novas:
        antigas[(str(r["ano"]), r["arquivo"])] = r
    campos = ["ano", "arquivo", "origem", "md5_csv", "linhas", "colunas", "destino", "registrado_em"]
    with caminho.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for chave in sorted(antigas):
            w.writerow(antigas[chave])
    print(f"\nManifesto da bronze: {caminho} ({len(antigas)} arquivos)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", required=True, help="ex.: 2019,2021,2023")
    p.add_argument("--arquivos", help=f"subconjunto de {','.join(ARQUIVOS)}")
    args = p.parse_args()
    filtro = {a.strip().upper() for a in args.arquivos.split(",")} if args.arquivos else None

    spark = criar_sessao("bronze-saeb")
    manifesto: list[dict] = []
    try:
        for ano in [int(a) for a in args.anos.split(",")]:
            processar(spark, ano, filtro, manifesto)
    finally:
        if manifesto:
            gravar_manifesto(manifesto)
        spark.stop()


if __name__ == "__main__":
    main()
