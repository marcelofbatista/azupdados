"""Carga BRONZE de um arquivo `microdados_ed_basica_<ano>.csv` do INEP.

O que este script garante:
  1. Linhagem: calcula o md5 do arquivo e, se houver, confere com o md5 oficial do INEP.
  2. Fidelidade: carrega TODAS as colunas como TEXT, sem nenhuma transformação.
     Tipagem e limpeza são responsabilidade da silver (dbt).
  3. Idempotência: recarregar o mesmo ano recria a tabela do zero.
  4. Formato aberto: grava uma cópia em Parquet particionada por ano.

Uso:
  python ingest/bronze_censo_escolar.py --arquivo data/landing/.../microdados_ed_basica_2024.csv --ano 2024
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

import psycopg
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
from psycopg import sql

FONTE = "inep_censo_escolar"
DELIMITADOR = ";"
BLOCO = 8 * 1024 * 1024


def md5_arquivo(caminho: Path) -> str:
    h = hashlib.md5()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(BLOCO), b""):
            h.update(bloco)
    return h.hexdigest()


def md5_oficial(caminho: Path | None) -> str | None:
    """Lê o arquivo md5 publicado pelo INEP (formato '<hash>  <nome>' ou só '<hash>')."""
    if caminho is None:
        return None
    m = re.search(r"\b[0-9a-fA-F]{32}\b", caminho.read_text(errors="ignore"))
    return m.group(0).lower() if m else None


def detectar_encoding(caminho: Path) -> tuple[str, str]:
    """Retorna (encoding Python, encoding PostgreSQL). O INEP historicamente usa LATIN1."""
    with caminho.open("rb") as f:
        amostra = f.read(4 * 1024 * 1024)
    try:
        amostra.decode("utf-8")
        return "utf-8", "UTF8"
    except UnicodeDecodeError:
        return "latin-1", "LATIN1"


def ler_cabecalho(caminho: Path, encoding: str) -> list[str]:
    with caminho.open("r", encoding=encoding, newline="") as f:
        linha = f.readline().strip().lstrip("﻿")
    colunas = [c.strip().strip('"').lower() for c in linha.split(DELIMITADOR)]
    if len(colunas) != len(set(colunas)):
        sys.exit("Cabeçalho com colunas duplicadas — investigar antes de carregar.")
    return colunas


def gravar_parquet(caminho: Path, colunas: list[str], encoding: str, ano: int) -> Path:
    destino = Path("data/bronze/censo_escolar") / f"ano={ano}" / "microdados_ed_basica.parquet"
    destino.parent.mkdir(parents=True, exist_ok=True)
    leitor = pacsv.open_csv(
        caminho,
        # blocos pequenos: pico de ~400 MB de RAM num arquivo de 370+ colunas (64 MB chegava a ~700 MB
        # e o processo foi morto por falta de memória num servidor compartilhado)
        read_options=pacsv.ReadOptions(encoding=encoding, block_size=8 * 1024 * 1024),
        parse_options=pacsv.ParseOptions(delimiter=DELIMITADOR),
        convert_options=pacsv.ConvertOptions(
            column_types={c: pa.string() for c in colunas},
            strings_can_be_null=False,
        ),
    )
    with pq.ParquetWriter(destino, leitor.schema, compression="zstd") as escritor:
        for lote in leitor:
            escritor.write_batch(lote)
    return destino


def carregar_postgres(caminho: Path, colunas: list[str], enc_pg: str, ano: int) -> tuple[str, int]:
    tabela = f"bronze.censo_escolar_escola_{ano}"
    # no Postgres as colunas ficam em minúsculas, sem aspas necessárias no SQL
    ddl_colunas = ",\n  ".join(f'"{c.lower()}" TEXT' for c in colunas)
    conninfo = (
        f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )
    with psycopg.connect(conninfo) as conn, conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {tabela}")
        cur.execute(f"CREATE TABLE {tabela} (\n  {ddl_colunas}\n)")
        copy_sql = (
            f"COPY {tabela} FROM STDIN WITH "
            f"(FORMAT csv, DELIMITER '{DELIMITADOR}', HEADER true, ENCODING '{enc_pg}')"
        )
        with cur.copy(copy_sql) as copy, caminho.open("rb") as f:
            for bloco in iter(lambda: f.read(BLOCO), b""):
                copy.write(bloco)
        cur.execute(f"SELECT count(*) FROM {tabela}")
        linhas = cur.fetchone()[0]
        comentario = f"BRONZE — {caminho.name}, carregado sem transformação (todas as colunas TEXT)."
        # COMMENT não aceita parâmetro; Literal faz o escape com segurança
        cur.execute(sql.SQL("COMMENT ON TABLE {} IS {}").format(
            sql.SQL(tabela), sql.Literal(comentario)))
        conn.commit()
    return tabela, linhas


def registrar_carga(ano, arquivo, md5, md5_ok, tabela, linhas, n_colunas) -> None:
    conninfo = (
        f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )
    with psycopg.connect(conninfo) as conn:
        conn.execute(
            """
            INSERT INTO meta.carga_arquivo
                (fonte, ano_referencia, arquivo, md5, md5_oficial_ok, tabela_destino, linhas, colunas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fonte, ano_referencia, md5) DO UPDATE
               SET linhas = EXCLUDED.linhas, colunas = EXCLUDED.colunas, carregado_em = now()
            """,
            (FONTE, ano, arquivo, md5, md5_ok, tabela, linhas, n_colunas),
        )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arquivo", required=True, type=Path)
    p.add_argument("--ano", required=True, type=int)
    p.add_argument("--md5-oficial", type=Path, help="arquivo md5 publicado pelo INEP (opcional)")
    p.add_argument("--sem-parquet", action="store_true")
    args = p.parse_args()

    if not args.arquivo.exists():
        sys.exit(f"Arquivo não encontrado: {args.arquivo}")

    print(f"[1/4] md5 de {args.arquivo.name} ...")
    md5 = md5_arquivo(args.arquivo)
    oficial = md5_oficial(args.md5_oficial)
    md5_ok = None if oficial is None else (oficial == md5)
    print(f"      md5={md5}  oficial={'n/d' if oficial is None else oficial}  confere={md5_ok}")
    if md5_ok is False:
        sys.exit("md5 NÃO confere com o oficial — arquivo corrompido ou diferente. Abortando.")

    enc_py, enc_pg = detectar_encoding(args.arquivo)
    colunas = ler_cabecalho(args.arquivo, enc_py)
    print(f"[2/4] encoding={enc_py}  colunas={len(colunas)}")

    if not args.sem_parquet:
        destino = gravar_parquet(args.arquivo, colunas, enc_py, args.ano)
        print(f"[3/4] Parquet gravado em {destino}")
    else:
        print("[3/4] Parquet pulado (--sem-parquet)")

    tabela, linhas = carregar_postgres(args.arquivo, colunas, enc_pg, args.ano)
    registrar_carga(args.ano, args.arquivo.name, md5, md5_ok, tabela, linhas, len(colunas))
    print(f"[4/4] {tabela}: {linhas:,} linhas × {len(colunas)} colunas — registrado em meta.carga_arquivo")


if __name__ == "__main__":
    main()
