"""Procura variáveis no dicionário oficial do SAEB (xlsx dentro do zip), sem extrair nada.

Os microdados do aluno não trazem sexo e cor/raça como colunas próprias: eles vêm do questionário
(TX_RESP_Q001, TX_RESP_Q01...), e o número da pergunta muda de uma edição para outra. Este script mostra,
para cada edição baixada, as linhas do dicionário que batem com os termos pedidos e as linhas seguintes
(onde ficam as categorias de resposta), para montar o de-para da silver a partir da fonte oficial.

Uso:
  python ingest/saeb_dicionario.py                          # termos padrão: sexo, cor, raça, INSE
  python ingest/saeb_dicionario.py --termos "sexo|cor|ra[cç]a" --contexto 10
"""

from __future__ import annotations

import argparse
import io
import re
import zipfile
from pathlib import Path

from openpyxl import load_workbook

LANDING = Path("data/landing/saeb/_zips")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--termos", default=r"\bsexo\b|\bcor\b|ra[cç]a|inse", help="expressão regular (sem maiúsculas)")
    p.add_argument("--contexto", type=int, default=8, help="linhas mostradas depois de cada achado")
    p.add_argument("--abas", default="aluno", help="só abas cujo nome contenha este texto (vazio = todas)")
    args = p.parse_args()
    termos = re.compile(args.termos, re.IGNORECASE)

    for zp in sorted(LANDING.glob("*.zip")):
        if "infantil" in zp.name.lower():
            continue
        with zipfile.ZipFile(zp) as z:
            dicionarios = [n for n in z.namelist() if n.lower().endswith(".xlsx") and "dicionario" in n.lower()
                           and "~$" not in n]
            for nome in dicionarios:
                wb = load_workbook(io.BytesIO(z.read(nome)), read_only=True, data_only=True)
                for ws in wb.worksheets:
                    if args.abas and args.abas.lower() not in ws.title.lower():
                        continue
                    linhas = [[str(c).strip() for c in r if c is not None] for r in ws.iter_rows(values_only=True)]
                    print(f"\n######## {zp.name} :: {Path(nome).name} :: aba '{ws.title}'")
                    mostradas: set[int] = set()
                    for i, r in enumerate(linhas):
                        texto = " | ".join(r)
                        if not termos.search(texto) or i in mostradas:
                            continue
                        print(f"\n--- linha {i + 1}")
                        for j in range(i, min(i + 1 + args.contexto, len(linhas))):
                            mostradas.add(j)
                            if linhas[j]:
                                print("   " + " | ".join(linhas[j])[:220])


if __name__ == "__main__":
    main()
