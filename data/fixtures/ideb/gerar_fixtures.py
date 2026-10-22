"""Gera planilhas SINTÉTICAS no layout das divulgações do IDEB 2025 (títulos, cabeçalho técnico na
linha 10, '-' como ausente, coluna sem nome, nome repetido, nota de rodapé). Valores inventados.

Uso: python data/fixtures/ideb/gerar_fixtures.py
"""
import io
import zipfile
from pathlib import Path

import openpyxl

AQUI = Path(__file__).parent
TITULO = [["Ministério da Educação"], ["Instituto Nacional de Estudos e Pesquisas"], [], ["Ensino Fundamental"],
          ["Indicadores educacionais"], [], ["rótulos legíveis"], ["subrótulos"], ["séries"]]


def metricas(anos, dup_2025=False):
    cols = []
    for a in anos:
        cols += [f"VL_APROVACAO_{a}_SI_4", f"VL_INDICADOR_REND_{a}", f"VL_NOTA_MATEMATICA_{a}",
                 f"VL_NOTA_PORTUGUES_{a}", f"VL_NOTA_MEDIA_{a}", f"VL_OBSERVADO_{a}"]
    if dup_2025:  # defeito real do INEP: a coluna de 2025 sai com o rótulo de 2023
        cols = [c.replace("VL_INDICADOR_REND_2025", "VL_INDICADOR_REND_2023") for c in cols]
    return cols + ["VL_PROJECAO_2021"]


def valores(n, base):
    return [str(round(base + i * 0.1, 1)) if i % 7 else "-" for i in range(n)]


def zipar(nome, abas):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for titulo, cabecalho, linhas in abas:
        ws = wb.create_sheet(titulo)
        for r in TITULO:
            ws.append(r)
        ws.append(cabecalho)
        for r in linhas:
            ws.append(r)
        ws.append(["Fonte: dados sintéticos para teste"])
    buf = io.BytesIO()
    wb.save(buf)
    with zipfile.ZipFile(AQUI / f"{nome}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{nome}/{nome}.xlsx", buf.getvalue())


anos = [2019, 2021, 2023, 2025]
m = metricas(anos)
zipar("divulgacao_anos_iniciais_escolas_2025", [("IDEB_Escolas (Anos_Iniciais)",
      ["SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "ID_ESCOLA", "NO_ESCOLA", "REDE"] + m,
      [["DF", 5300108, "Brasília", 53000001, "ESCOLA SINTETICA A", "Estadual"] + valores(len(m), 5),
       ["AL", 2704302, "Maceió", 27000002, "ESCOLA SINTETICA B", "Municipal"] + ["-"] * len(m)])])
zipar("divulgacao_anos_iniciais_municipios_2025", [("IDEB_AI_MUNICÍPIOS",
      ["SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "REDE"] + m,
      [["DF", 5300108, "Brasília", "Estadual"] + valores(len(m), 5),
       ["DF", 5300108, "Brasília", "Pública"] + valores(len(m), 5)])])
md = metricas(anos, dup_2025=True)
zipar("divulgacao_regioes_ufs_ideb_2025", [(f"UF e Regiões ({e})", [None, None] + md,
      [["Centro-Oeste", "Total"] + valores(len(md), 5), ["Distrito Federal", "Pública"] + valores(len(md), 5)])
      for e in ("AI", "AF", "EM")])
zipar("divulgacao_brasil_ideb_2025", [(f"Brasil ({e})", ["BRASIL", "rede"] + md,
      [["Brasil", "Total"] + valores(len(md), 5)]) for e in ("Anos Iniciais", "Anos Finais", "EM")])
print("fixtures geradas em", AQUI)
