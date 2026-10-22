"""Carga BRONZE dos indicadores educacionais do INEP por escola (landing de baixar_indicadores_inep.py).

Cada arquivo vira uma tabela só-texto, com o cabeçalho técnico do INEP como veio (em minúsculas):

  bronze.ind_<sigla>_<ano>          ex.: bronze.ind_rend_2015, bronze.ind_tdi_2025, bronze.ind_inse_2023
  bronze.ind_colunas                dicionário: sigla, ano, posição, nome técnico, rótulo (linhas de título
                                    acima do cabeçalho técnico, com células mescladas propagadas)

Cuidados (armadilha 12):
  - Cada zip traz o MESMO conteúdo em .xlsx e .ods, mais um md5 oficial do INEP. Carrega só o .xlsx e confere
    o md5 dele contra o arquivo oficial (meta.carga_arquivo.md5_oficial_ok).
  - O cabeçalho técnico é a linha que contém o código da escola: CO_ENTIDADE, PK_COD_ENTIDADE (2015),
    CO_ESCOLA ou ID_ESCOLA (INSE). Acima dela há 4 a 10 linhas de título; abaixo dos dados, notas de rodapé
    (linhas sem código de escola), que são descartadas.
  - Os nomes técnicos mudam de geração (tap_F14 → 1_CAT_FUN_AI). A bronze NÃO traduz: a silver faz o de-para.
  - "--" é ausência de dado (não zero). Fica como texto aqui; a silver converte em NULL.

Uso:
  python ingest/bronze_indicadores.py --so-cabecalhos     # só lista os cabeçalhos técnicos (sem banco)
  python ingest/bronze_indicadores.py                     # carga completa
  python ingest/bronze_indicadores.py --indicadores TDI --anos 2024,2025
  python ingest/bronze_indicadores.py --pasta data/fixtures/indicadores   # fixtures sintéticas (CI)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import re
import sys
import zipfile
from pathlib import Path

import openpyxl

CHAVES_ESCOLA = {"co_entidade", "pk_cod_entidade", "co_escola", "id_escola"}
SIGLA_DA_PASTA = {"rendimento": "REND", "tdi": "TDI", "atu": "ATU", "had": "HAD", "afd": "AFD",
                  "ird": "IRD", "ied": "IED", "icg": "ICG", "inse": "INSE"}


def texto(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    return s or None


def nome_tecnico(v, i: int) -> str:
    s = (texto(v) or f"col_{i + 1}").lower()
    return re.sub(r"[^a-z0-9_]", "_", s)


def md5_oficiais(z: zipfile.ZipFile) -> dict[str, str]:
    """{nome do arquivo em minúsculas: md5} a partir dos .txt de md5 que o INEP põe no zip."""
    saida = {}
    for n in z.namelist():
        if "md5" in n.lower() and n.lower().endswith(".txt"):
            for linha in z.read(n).decode("latin-1").splitlines():
                m = re.match(r"\s*([0-9a-fA-F]{32})\s+\*?(.+?)\s*$", linha)
                if m:
                    saida[Path(m[2]).name.lower()] = m[1].lower()
    return saida


def abrir_planilha(arq: Path) -> tuple[bytes, str, bool | None]:
    """(bytes do xlsx, nome interno, md5 oficial confere?)."""
    if arq.suffix.lower() == ".xlsx":
        return arq.read_bytes(), arq.name, None
    with zipfile.ZipFile(arq) as z:
        xlsx = [n for n in z.namelist() if n.lower().endswith(".xlsx") and not n.startswith("__MACOSX")]
        if len(xlsx) != 1:
            sys.exit(f"{arq}: esperava 1 .xlsx no zip, achei {xlsx}")
        dados = z.read(xlsx[0])
        oficial = md5_oficiais(z).get(Path(xlsx[0]).name.lower())
        confere = None if oficial is None else hashlib.md5(dados).hexdigest() == oficial
        if confere is False:
            sys.exit(f"{arq}/{xlsx[0]}: md5 NÃO confere com o oficial do INEP — arquivo corrompido?")
        return dados, xlsx[0], confere


def ler(dados: bytes) -> tuple[list[str], list[str], list[list[str | None]], str]:
    """(nomes técnicos, rótulos, linhas de dados, aba). Usa a primeira aba que tem o cabeçalho técnico."""
    wb = openpyxl.load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
    for ws in wb.worksheets:
        titulo, cab, linhas = [], None, ws.iter_rows(values_only=True)
        for linha in linhas:
            if any(isinstance(c, str) and c.strip().lower() in CHAVES_ESCOLA for c in linha):
                cab = list(linha)
                break
            titulo.append(list(linha))
            if len(titulo) > 30:
                break
        if cab is None:
            continue
        while cab and cab[-1] is None:
            cab.pop()

        nomes, vistos = [], {}
        for i, c in enumerate(cab):
            n = nome_tecnico(c, i)
            vistos[n] = vistos.get(n, 0) + 1
            nomes.append(n if vistos[n] == 1 else f"{n}__{vistos[n]}")

        # rótulo: linhas de título acima, com a célula mesclada propagada para a direita
        partes = [[] for _ in nomes]
        for t in titulo:
            atual = None
            for i in range(len(nomes)):
                v = texto(t[i]) if i < len(t) else None
                if v is not None:
                    atual = v
                elif i < 9:  # colunas de identificação não herdam o vizinho
                    atual = None
                if atual and (not partes[i] or partes[i][-1] != atual):
                    partes[i].append(atual)
        rotulos = [" / ".join(p[-3:]) for p in partes]

        pos_id = next(i for i, n in enumerate(nomes) if n.split("__")[0] in CHAVES_ESCOLA)
        dados_linhas = []
        for linha in linhas:
            valores = [texto(c) for c in linha][: len(nomes)]
            valores += [None] * (len(nomes) - len(valores))
            if valores[pos_id] and valores[pos_id].isdigit():  # descarta notas de rodapé
                dados_linhas.append(valores)
        return nomes, rotulos, dados_linhas, ws.title
    sys.exit("Cabeçalho técnico (código da escola) não encontrado em nenhuma aba")


def ano_do_manifesto(pasta: Path) -> dict[str, int]:
    man = pasta / "_manifesto.csv"
    if not man.exists():
        return {}
    with man.open() as f:
        return {Path(r["arquivo"]).name: int(r["ano"]) for r in csv.DictReader(f)}


def arquivos(pasta: Path, sigs: set[str], anos: set[int] | None) -> list[tuple[str, int, Path]]:
    ano_de = ano_do_manifesto(pasta)
    saida = []
    for sub in sorted(p for p in pasta.iterdir() if p.is_dir() and p.name in SIGLA_DA_PASTA):
        sig = SIGLA_DA_PASTA[sub.name]
        if sig not in sigs:
            continue
        for arq in sorted(sub.glob("*")):
            if arq.suffix.lower() not in (".zip", ".xlsx") or arq.name.endswith(".part"):
                continue
            ano = ano_de.get(arq.name)
            if ano is None:
                m = re.search(r"(20\d\d)(?!.*20\d\d)", arq.name)
                ano = int(m[1]) if m else 2013 if "INSE_por_Escola" in arq.name else None
            if ano is None:
                sys.exit(f"Não sei o ano de {arq}")
            if anos is None or ano in anos:
                saida.append((sig, ano, arq))
    return saida


def conninfo() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )


def carregar(conn, sig, ano, arq, nomes, rotulos, linhas, interno, confere) -> None:
    from psycopg import sql

    tabela = f"ind_{sig.lower()}_{ano}"
    ident = sql.Identifier("bronze", tabela)
    md5_zip = hashlib.md5(arq.read_bytes()).hexdigest()
    with conn.cursor() as cur:
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(ident))
        cur.execute(sql.SQL("CREATE TABLE {} ({})").format(
            ident, sql.SQL(", ").join(sql.SQL("{} TEXT").format(sql.Identifier(n)) for n in nomes)))
        with cur.copy(sql.SQL("COPY {} FROM STDIN").format(ident)) as cp:
            for linha in linhas:
                cp.write_row(linha)
        cur.execute(sql.SQL("COMMENT ON TABLE {} IS {}").format(
            ident, sql.Literal(f"BRONZE — INEP indicador {sig} {ano} por escola ({arq.name}/{interno}), sem transformação.")))
        cur.execute("""CREATE TABLE IF NOT EXISTS bronze.ind_colunas (
                         sigla text, ano int, posicao int, nome_tecnico text, rotulo text, tabela text)""")
        cur.execute("DELETE FROM bronze.ind_colunas WHERE sigla = %s AND ano = %s", (sig, ano))
        cur.executemany(
            "INSERT INTO bronze.ind_colunas VALUES (%s, %s, %s, %s, %s, %s)",
            [(sig, ano, i + 1, n, r or None, f"bronze.{tabela}") for i, (n, r) in enumerate(zip(nomes, rotulos))],
        )
        cur.execute(
            """INSERT INTO meta.carga_arquivo
                 (fonte, ano_referencia, arquivo, md5, md5_oficial_ok, tabela_destino, linhas, colunas)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (fonte, ano_referencia, md5) DO UPDATE
                 SET linhas = EXCLUDED.linhas, colunas = EXCLUDED.colunas,
                     md5_oficial_ok = EXCLUDED.md5_oficial_ok, carregado_em = now()""",
            (f"inep_ind_{sig.lower()}", ano, f"{arq.name}/{interno}", md5_zip, confere,
             f"bronze.{tabela}", len(linhas), len(nomes)),
        )
    conn.commit()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pasta", type=Path, default=Path("data/landing/indicadores"))
    p.add_argument("--indicadores", default=",".join(SIGLA_DA_PASTA.values()))
    p.add_argument("--anos", help="ex.: 2015-2025 | 2024,2025")
    p.add_argument("--so-cabecalhos", action="store_true", help="só imprime os cabeçalhos técnicos (sem banco)")
    args = p.parse_args()

    anos = None
    if args.anos:
        if "-" in args.anos:
            ini, fim = (int(x) for x in args.anos.split("-"))
            anos = set(range(ini, fim + 1))
        else:
            anos = {int(x) for x in args.anos.split(",")}
    lista = arquivos(args.pasta, {s.strip().upper() for s in args.indicadores.split(",")}, anos)
    if not lista:
        sys.exit(f"Nenhum arquivo de indicador em {args.pasta}")

    conn = None
    if not args.so_cabecalhos:
        import psycopg

        conn = psycopg.connect(conninfo())
    try:
        for sig, ano, arq in lista:
            dados, interno, confere = abrir_planilha(arq)
            nomes, rotulos, linhas, aba = ler(dados)
            md5 = {True: "md5 ok", False: "md5 FALHOU", None: "sem md5 oficial"}[confere]
            print(f"{sig:4} {ano}  {len(linhas):>7,} escolas × {len(nomes):>3} col  [{md5}]  aba '{aba}'")
            if args.so_cabecalhos:
                print("      " + " ".join(nomes))
                continue
            carregar(conn, sig, ano, arq, nomes, rotulos, linhas, interno, confere)
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
