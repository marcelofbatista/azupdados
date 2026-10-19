"""Carga BRONZE das respostas do SEDAP+ salvas por `sedap_tipo_deficiencia.py`.

Lê todos os JSON de uma pasta e grava duas tabelas, recriadas a cada execução (idempotente):

  bronze.sedap_ee_tipo              uma linha por ano × UF × dependência × métrica (formato longo,
                                    resistente a métricas novas ou renomeadas)
  bronze.sedap_ee_tipo_estatisticas estatísticas de privacidade diferencial que o SEDAP+ devolve por
                                    métrica (taxa de ruído, média, mediana, IC 95%)

Tudo entra como TEXT, sem transformação. Tipagem é responsabilidade da silver (dbt).

Uso:
  python ingest/bronze_sedap.py                                   # data/landing/sedap/tipo_deficiencia
  python ingest/bronze_sedap.py --pasta data/fixtures/sedap       # fixtures sintéticas (CI)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import psycopg

CHAVES = {"co_uf", "tp_dependencia"}

DDL = """
DROP TABLE IF EXISTS bronze.sedap_ee_tipo CASCADE;  -- views da silver são recriadas pelo dbt
CREATE TABLE bronze.sedap_ee_tipo (
  ano text, co_uf text, tp_dependencia text, metrica text, valor text,
  excluiu_aee text, extraido_em text, arquivo text, md5 text
);
COMMENT ON TABLE bronze.sedap_ee_tipo IS
  'BRONZE — respostas do SEDAP+ (INEP, privacidade diferencial) em formato longo, sem transformação.';
DROP TABLE IF EXISTS bronze.sedap_ee_tipo_estatisticas CASCADE;
CREATE TABLE bronze.sedap_ee_tipo_estatisticas (
  ano text, metrica text, coluna_inep text, funcao text, taxa_ruido text,
  media text, mediana text, nivel_confianca text, ic_inferior text, ic_superior text, arquivo text
);
COMMENT ON TABLE bronze.sedap_ee_tipo_estatisticas IS
  'BRONZE — estatísticas de privacidade diferencial devolvidas pelo SEDAP+ para cada métrica.';
"""


def conninfo() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )


def texto(v) -> str | None:
    return None if v is None else str(v)


def colunas_estatisticas(bloco) -> list[dict]:
    """Acha a lista de estatísticas por coluna, esteja ela no topo ou aninhada num dicionário.

    A API devolve `bqconnector_statistics` como dicionário (com perdas de linha/grupo e a lista de
    colunas dentro); a busca é genérica para não quebrar se o INEP mudar a chave.
    """
    if isinstance(bloco, list):
        if bloco and all(isinstance(x, dict) and "results" in x for x in bloco):
            return bloco
        for x in bloco:
            achado = colunas_estatisticas(x)
            if achado:
                return achado
    elif isinstance(bloco, dict):
        for v in bloco.values():
            achado = colunas_estatisticas(v)
            if achado:
                return achado
    return []


def ler(arq: Path) -> tuple[list[tuple], list[tuple]]:
    bruto = arq.read_bytes()
    md5 = hashlib.md5(bruto).hexdigest()
    reg = json.loads(bruto)
    resp = reg["resposta"]
    if not resp.get("success", True):
        sys.exit(f"{arq.name}: resposta do SEDAP+ sem sucesso — não carregar.")

    linhas = []
    for row in resp["rows"]:
        r = {k.lower(): v for k, v in row.items()}
        for metrica, valor in r.items():
            if metrica in CHAVES:
                continue
            linhas.append((
                str(reg["ano"]), texto(r["co_uf"]), texto(r["tp_dependencia"]), metrica, texto(valor),
                str(reg.get("excluiu_aee")), reg.get("extraido_em"), arq.name, md5,
            ))

    estat = []
    for c in colunas_estatisticas(resp.get("bqconnector_statistics")):
        res = c.get("results", {})
        ic = res.get("confidence_interval", {}).get("final", {})
        estat.append((
            str(reg["ano"]), c.get("resolved_name"), c.get("base_name"), c.get("aggregation_fn"),
            texto(res.get("noise_rate")), texto(res.get("average", {}).get("final")),
            texto(res.get("median", {}).get("final")), texto(ic.get("confidence_level")),
            texto(ic.get("lower_bound")), texto(ic.get("upper_bound")), arq.name,
        ))
    return linhas, estat


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pasta", type=Path, default=Path("data/landing/sedap/tipo_deficiencia"))
    args = p.parse_args()

    arquivos = sorted(args.pasta.glob("*.json"))
    if not arquivos:
        sys.exit(f"Nenhum JSON em {args.pasta}")

    linhas, estat = [], []
    for arq in arquivos:
        lin, est = ler(arq)
        linhas += lin
        estat += est
        print(f"  {arq.name}: {len(lin)} valores, {len(est)} métricas com estatística")

    with psycopg.connect(conninfo()) as conn, conn.cursor() as cur:
        cur.execute(DDL)
        with cur.copy("COPY bronze.sedap_ee_tipo FROM STDIN") as cp:
            for r in linhas:
                cp.write_row(r)
        with cur.copy("COPY bronze.sedap_ee_tipo_estatisticas FROM STDIN") as cp:
            for r in estat:
                cp.write_row(r)
        conn.commit()
    print(f"bronze.sedap_ee_tipo: {len(linhas):,} linhas · bronze.sedap_ee_tipo_estatisticas: {len(estat)} linhas")


if __name__ == "__main__":
    main()
