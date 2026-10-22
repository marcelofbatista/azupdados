"""Carga BRONZE das planilhas de divulgação do IDEB (INEP).

As planilhas de 2025 trazem a série inteira desde 2005 (2017 no ensino médio). Cada arquivo vira uma
tabela só-texto, com o cabeçalho técnico do INEP (SG_UF, VL_OBSERVADO_2023...) e nenhuma transformação:

  bronze.ideb_<nivel>_<etapa>     nivel: escola | municipio | uf | brasil     etapa: ai | af | em

Cuidados (armadilha 11):
  - O cabeçalho técnico fica na linha que contém as colunas VL_*, depois de linhas de título.
  - Nas planilhas de UF e de Brasil, as colunas de identificação vêm SEM nome no cabeçalho técnico.
  - O INEP repete nomes de coluna (ex.: VL_INDICADOR_REND_2023 duas vezes, a segunda é 2025). A segunda
    ocorrência ganha o sufixo __2; a silver decide o que ela é. Nada é descartado aqui.
  - Linhas de nota de rodapé (sem nenhum valor VL_*) são ignoradas.

Uso:
  python ingest/bronze_ideb.py                             # data/landing/ideb, arquivos de 2025
  python ingest/bronze_ideb.py --pasta data/fixtures/ideb  # fixtures sintéticas (CI)
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

import openpyxl
import psycopg
from psycopg import sql

FONTE = "inep_ideb"
PADROES = ("*escolas_2025*.zip", "*municipios_2025*.zip", "*regioes_ufs*2025*.zip", "*brasil*2025*.zip")
NIVEL = {"escolas": "escola", "municipios": "municipio", "regioes_ufs": "uf", "brasil": "brasil"}
# nomes padronizados para as colunas de identificação dos agregados (no arquivo de UF elas vêm sem nome;
# no de Brasil, como "BRASIL" e "rede")
ID_SEM_NOME = {"uf": ["no_regiao_uf", "rede"], "brasil": ["no_brasil", "rede"]}


def sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def nivel_de(arquivo: str) -> str:
    for chave, nivel in NIVEL.items():
        if chave in arquivo:
            return nivel
    sys.exit(f"Não sei o nível do arquivo {arquivo}")


def etapa_de(arquivo: str, aba: str) -> str:
    t = sem_acento(f"{arquivo} {aba}")
    if "inicia" in t or "(ai)" in t or "_ai_" in t:
        return "ai"
    if "finais" in t or "(af)" in t or "_af_" in t:
        return "af"
    if "medio" in t or "(em)" in t:
        return "em"
    sys.exit(f"Não sei a etapa de {arquivo} / {aba}")


def texto(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    return s or None


def ler_aba(ws, nivel: str) -> tuple[list[str], list[list[str | None]]]:
    linhas = ws.iter_rows(values_only=True)
    for linha in linhas:
        if any(isinstance(c, str) and c.strip().upper().startswith("VL_") for c in linha):
            cabecalho_bruto = list(linha)
            break
    else:
        sys.exit("Cabeçalho técnico (colunas VL_*) não encontrado")

    nomes, vistos = [], {}
    padrao = ID_SEM_NOME.get(nivel, [])
    for i, c in enumerate(cabecalho_bruto):
        nome = padrao[i] if i < len(padrao) else (texto(c) or f"col_{i + 1}").lower()
        if nome in vistos:
            vistos[nome] += 1
            nome = f"{nome}__{vistos[nome]}"
        else:
            vistos[nome] = 1
        nomes.append(nome)

    pos_vl = [i for i, n in enumerate(nomes) if n.startswith("vl_")]
    dados = []
    for linha in linhas:
        valores = [texto(c) for c in linha][: len(nomes)]
        valores += [None] * (len(nomes) - len(valores))
        if any(valores[i] is not None for i in pos_vl):
            dados.append(valores)
    return nomes, dados


def conninfo() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST', '127.0.0.1')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )


def carregar(conn, tabela: str, nomes: list[str], dados: list, origem: str, md5: str) -> None:
    ident = sql.Identifier("bronze", tabela)
    with conn.cursor() as cur:
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(ident))  # views da silver: o dbt recria
        cur.execute(sql.SQL("CREATE TABLE {} ({})").format(
            ident, sql.SQL(", ").join(sql.SQL("{} TEXT").format(sql.Identifier(n)) for n in nomes)))
        with cur.copy(sql.SQL("COPY {} FROM STDIN").format(ident)) as cp:
            for linha in dados:
                cp.write_row(linha)
        cur.execute(sql.SQL("COMMENT ON TABLE {} IS {}").format(
            ident, sql.Literal(f"BRONZE — {origem}, sem transformação (todas as colunas TEXT).")))
        cur.execute(
            """INSERT INTO meta.carga_arquivo
                 (fonte, ano_referencia, arquivo, md5, md5_oficial_ok, tabela_destino, linhas, colunas)
               VALUES (%s, 2025, %s, %s, NULL, %s, %s, %s)
               ON CONFLICT (fonte, ano_referencia, md5) DO UPDATE
                 SET linhas = EXCLUDED.linhas, colunas = EXCLUDED.colunas, carregado_em = now()""",
            (FONTE, origem, md5, f"bronze.{tabela}", len(dados), len(nomes)),
        )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pasta", type=Path, default=Path("data/landing/ideb"))
    args = p.parse_args()

    zips = sorted({z for padrao in PADROES for z in args.pasta.glob(padrao)})
    if not zips:
        sys.exit(f"Nenhuma planilha de 2025 do IDEB em {args.pasta}")

    with psycopg.connect(conninfo()) as conn:
        for z in zips:
            bruto = z.read_bytes()
            md5 = hashlib.md5(bruto).hexdigest()
            nivel = nivel_de(z.name)
            with zipfile.ZipFile(io.BytesIO(bruto)) as zf:
                for interno in (n for n in zf.namelist() if n.lower().endswith(".xlsx")):
                    wb = openpyxl.load_workbook(io.BytesIO(zf.read(interno)), read_only=True, data_only=True)
                    for ws in wb.worksheets:
                        etapa = etapa_de(Path(interno).name, ws.title)
                        nomes, dados = ler_aba(ws, nivel)
                        tabela = f"ideb_{nivel}_{etapa}"
                        dup = [n for n in nomes if re.search(r"__\d+$", n)]
                        carregar(conn, tabela, nomes, dados, f"{z.name}/{ws.title}", md5)
                        aviso = f" | nomes repetidos: {dup}" if dup else ""
                        print(f"  bronze.{tabela}: {len(dados):,} linhas × {len(nomes)} colunas{aviso}")
        conn.commit()


if __name__ == "__main__":
    main()
