"""BRONZE das médias oficiais do SAEB (planilhas TS_BRASIL e TS_UF que o INEP põe dentro do zip).

É o gabarito da reconciliação: a média ponderada calculada a partir dos alunos tem de reproduzir estes números.
Só as colunas MEDIA_* entram (as nivel_* são distribuição por nível de proficiência, ficam para depois).
Formato longo e tudo como texto, como nas demais bronzes; a tipagem é feita no dbt.

Layout confirmado em 2019 e 2021: cabeçalho na linha 1; TS_BRASIL começa com ID, TS_UF com CO_UF e NO_UF;
depois DEPENDENCIA_ADM, LOCALIZACAO, CAPITAL e as colunas MEDIA_<série>_<disciplina>.
A edição 2023 não traz essas planilhas no zip.

Uso:
  python ingest/bronze_saeb_resultados.py                         # zips de data/landing/saeb/_zips
  python ingest/bronze_saeb_resultados.py --pasta data/fixtures/saeb
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import zipfile
from pathlib import Path

import psycopg
from openpyxl import load_workbook

FONTE = "inep_saeb_resultado_oficial"
TABELA = "bronze.saeb_resultado_oficial"
PLANILHAS = {"TS_BRASIL.XLSX": "BRASIL", "TS_UF.XLSX": "UF"}


def conninfo() -> str:
    return (f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} port={os.environ.get('POSTGRES_PORT', '5432')} "
            f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
            f"password={os.environ['POSTGRES_PASSWORD']}")


def ano_do_zip(nome: str) -> int | None:
    m = re.search(r"saeb_(\d{4})", nome)
    return int(m.group(1)) if m else None


def ler(conteudo: bytes, abrangencia: str, ano: int, arquivo: str) -> list[tuple]:
    ws = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True).worksheets[0]
    linhas = ws.iter_rows(values_only=True)
    cab = [str(c).strip().upper() if c is not None else "" for c in next(linhas)]
    pos = {c: i for i, c in enumerate(cab)}
    medias = [(i, c) for i, c in enumerate(cab) if c.startswith("MEDIA_")]
    saida = []
    for r in linhas:
        if not any(v is not None for v in r):
            continue
        def v(nome: str, linha: tuple = r) -> str | None:
            i = pos.get(nome)
            return None if i is None or linha[i] is None else str(linha[i]).strip()

        co_uf = v("CO_UF") if abrangencia == "UF" else None
        for i, coluna in medias:
            valor = r[i]
            if valor is None or str(valor).strip() == "":
                continue
            saida.append((str(ano), abrangencia, co_uf, v("DEPENDENCIA_ADM"), v("LOCALIZACAO"), v("CAPITAL"),
                          coluna, repr(float(valor)) if isinstance(valor, (int, float)) else str(valor), arquivo))
    return saida


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pasta", default="data/landing/saeb/_zips")
    args = p.parse_args()

    with psycopg.connect(conninfo()) as conn, conn.cursor() as cur:
        cur.execute(Path("sql/init/02_saeb.sql").read_text())
        for zp in sorted(Path(args.pasta).glob("*.zip")):
            ano = ano_do_zip(zp.name)
            if ano is None or "infantil" in zp.name.lower():
                continue
            with zipfile.ZipFile(zp) as z:
                for nome in z.namelist():
                    abrangencia = PLANILHAS.get(Path(nome).name.upper())
                    if not abrangencia:
                        continue
                    conteudo = z.read(nome)
                    linhas = ler(conteudo, abrangencia, ano, f"{zp.name}::{nome}")
                    cur.execute(f"delete from {TABELA} where ano = %s and abrangencia = %s", (str(ano), abrangencia))
                    with cur.copy(f"copy {TABELA} (ano, abrangencia, co_uf, dependencia_adm, localizacao, capital, "
                                  "coluna, valor, arquivo) from stdin") as cp:
                        for linha in linhas:
                            cp.write_row(linha)
                    cur.execute(
                        """insert into meta.carga_arquivo
                               (fonte, ano_referencia, arquivo, md5, md5_oficial_ok, tabela_destino, linhas, colunas)
                           values (%s, %s, %s, %s, null, %s, %s, null)
                           on conflict (fonte, ano_referencia, md5) do update
                              set linhas = excluded.linhas, carregado_em = now()""",
                        (FONTE, ano, f"{zp.name}::{nome}", hashlib.md5(conteudo).hexdigest(), TABELA, len(linhas)))
                    print(f"{ano} {abrangencia:<6} {len(linhas):>6,} médias  ← {zp.name}::{nome}")

        cur.execute(f"""select abrangencia, string_agg(distinct dependencia_adm, ', '),
                               string_agg(distinct localizacao, ', '), string_agg(distinct capital, ', ')
                        from {TABELA} group by 1 order by 1""")
        print("\nValores encontrados (dependência | localização | capital):")
        for a, d, loc, cap in cur.fetchall():
            print(f"  {a}: {d} | {loc} | {cap}")


if __name__ == "__main__":
    main()
