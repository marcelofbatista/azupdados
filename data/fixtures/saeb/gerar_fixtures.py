"""Gera as fixtures sintéticas do SAEB usadas no CI (o Spark não roda no CI).

- saeb_agregado.csv: linhas no formato de silver.saeb_agregado (o que o PySpark produziria);
- microdados_saeb_2019.zip: com PLANILHAS DE RESULTADOS/TS_BRASIL.xlsx e TS_UF.xlsx mínimas, no layout real.
Os números são inventados, mas coerentes entre si: a média do agregado é a média das planilhas.

Uso:  python data/fixtures/saeb/gerar_fixtures.py
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

from openpyxl import Workbook

PASTA = Path(__file__).parent
CAMPOS = ["ano", "arquivo", "id_serie", "id_uf", "in_publica", "id_localizacao", "id_area", "disciplina",
          "cor_raca_censo", "sexo_codigo", "nivel_inse", "in_situacao_censo", "n_alunos", "n_presentes",
          "n_com_proficiencia", "soma_peso", "soma_peso_prof", "soma_peso_prof2"]

# (arquivo, série, UF, pública, disciplina, cor, peso total, média)
GRUPOS = [
    ("5EF", 5, 53, 1, "LP", 1, 100.0, 210.0), ("5EF", 5, 53, 0, "LP", 3, 50.0, 240.0),
    ("5EF", 5, 52, 1, "LP", 2, 50.0, 200.0), ("5EF", 5, 53, 1, "MT", 1, 100.0, 220.0),
    ("9EF", 9, 53, 1, "LP", 3, 80.0, 255.0), ("34EM", 12, 53, 1, "MT", None, 60.0, 275.0),
]


def media(filtro) -> float:
    g = [x for x in GRUPOS if filtro(x)]
    return round(sum(x[6] * x[7] for x in g) / sum(x[6] for x in g), 2)


def planilha(abrangencia: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ident = ["ID"] if abrangencia == "BRASIL" else ["CO_UF", "NO_UF"]
    ws.append([*ident, "DEPENDENCIA_ADM", "LOCALIZACAO", "CAPITAL", "MEDIA_5_LP", "MEDIA_5_MT", "MEDIA_9_LP"])
    if abrangencia == "BRASIL":
        ws.append(["Brasil", "Total - Federal, Estadual, Municipal e Privada", "Total", "Total", media(lambda x: x[0] == "5EF" and x[4] == "LP"),
                   media(lambda x: x[0] == "5EF" and x[4] == "MT"), media(lambda x: x[0] == "9EF")])
    else:
        ws.append([53, "Distrito Federal", "Total - Federal, Estadual, Municipal e Privada", "Total", "Total",
                   media(lambda x: x[0] == "5EF" and x[4] == "LP" and x[2] == 53),
                   media(lambda x: x[0] == "5EF" and x[4] == "MT" and x[2] == 53), media(lambda x: x[0] == "9EF")])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def main() -> None:
    with (PASTA / "saeb_agregado.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CAMPOS)
        for arq, serie, uf, pub, disc, cor, peso, med in GRUPOS:
            w.writerow([2019, arq, serie, uf, pub, 1, 2, disc, "" if cor is None else cor, "", "", 1,
                        int(peso), int(peso), int(peso), peso, peso * med, peso * med * med])
    with zipfile.ZipFile(PASTA / "microdados_saeb_2019.zip", "w") as z:
        z.writestr("PLANILHAS DE RESULTADOS/TS_BRASIL.xlsx", planilha("BRASIL"))
        z.writestr("PLANILHAS DE RESULTADOS/TS_UF.xlsx", planilha("UF"))
    print("fixtures do SAEB geradas em", PASTA)


if __name__ == "__main__":
    main()
