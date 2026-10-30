"""Mostra o começo das planilhas oficiais de resultados do SAEB (TS_BRASIL, TS_UF) que vêm dentro dos zips.

São o "gabarito" da reconciliação: a média ponderada que o azupdados calcula a partir dos alunos tem de bater
com a média que o próprio INEP publica. Antes de escrever o leitor, este script mostra o layout real.

Uso:  python ingest/saeb_resultados_inspecionar.py [--linhas 6]
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

from openpyxl import load_workbook


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--linhas", type=int, default=6)
    args = p.parse_args()
    for zp in sorted(Path("data/landing/saeb/_zips").glob("*.zip")):
        with zipfile.ZipFile(zp) as z:
            for nome in z.namelist():
                base = Path(nome).name.upper()
                if base not in ("TS_BRASIL.XLSX", "TS_UF.XLSX"):
                    continue
                wb = load_workbook(io.BytesIO(z.read(nome)), read_only=True, data_only=True)
                for ws in wb.worksheets:
                    linhas = list(ws.iter_rows(values_only=True, max_row=args.linhas))
                    largura = max((len(r) for r in linhas), default=0)
                    print(f"\n#### {zp.name} :: {base} :: aba '{ws.title}' ({largura} colunas)")
                    for r in linhas:
                        print("   " + " | ".join("" if c is None else str(c) for c in r)[:1500])


if __name__ == "__main__":
    main()
