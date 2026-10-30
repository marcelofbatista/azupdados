"""Download (LANDING) e inventário dos microdados do SAEB (INEP).

Três modos:
  --sondar      testa as grafias conhecidas de cada edição e mostra o que existe (1 byte por arquivo)
  (padrão)      baixa os zips para data/landing/saeb/_zips/ e grava o manifesto com md5
  --inventario  lista o conteúdo de cada zip baixado SEM extrair: nome, tamanho, e a primeira linha
                (cabeçalho) de cada CSV. Grava data/landing/saeb/_inventario.csv. É o que define o layout
                antes de escrever a leitura em PySpark.

O SAEB é bienal (anos ímpares). Até 2013 o arquivo se chamava "aneb_prova_brasil"; a partir de 2021 o INEP
separou ensino fundamental/médio e educação infantil. Como nos indicadores, nada é adivinhado fora das
variantes abaixo: edição não encontrada aparece no relatório e o link certo, copiado do site, entra em
CAMINHOS_EXPLICITOS ou no parâmetro --url.

Usa o mesmo certificado intermediário dos demais downloads do INEP (make certs-inep).

Uso:
  python ingest/baixar_saeb_inep.py --sondar
  python ingest/baixar_saeb_inep.py --anos 2019,2021,2023
  python ingest/baixar_saeb_inep.py --inventario
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import baixar_indicadores_inep as inep

BASES = ["https://download.inep.gov.br/microdados", "https://download.inep.gov.br/dados_abertos"]
DESTINO = Path("data/landing/saeb")
EDICOES = [2011, 2013, 2015, 2017, 2019, 2021, 2023]

# Grafias que o INEP já usou para o SAEB. Para 2021+ pode haver mais de um arquivo por edição
# (fundamental/médio e infantil); todos os que existirem são baixados.
def VARIANTES(ano: int) -> list[list[str]]:
    """Grupos de candidatos: de cada grupo vale o primeiro que existir."""
    grupos = [[f"microdados_saeb_{ano}.zip", f"microdados_SAEB_{ano}.zip"]]
    if ano <= 2013:
        grupos = [[f"microdados_aneb_prova_brasil_{ano}.zip", f"microdados_prova_brasil_{ano}.zip",
                   f"microdados_saeb_{ano}.zip"]]
    if ano >= 2021:
        grupos = [
            [f"microdados_saeb_{ano}_ensino_fundamental_e_medio.zip",
             f"microdados_saeb_{ano}_ensino_fundamental_medio.zip", f"microdados_saeb_{ano}.zip"],
            [f"microdados_saeb_{ano}_educacao_infantil.zip"],
        ]
    return grupos


CAMINHOS_EXPLICITOS: dict[int, list[str]] = {}  # ano -> URLs completas copiadas do site, se as variantes falharem


def localizar(ano: int) -> list[dict]:
    achados = []
    if ano in CAMINHOS_EXPLICITOS:
        for url in CAMINHOS_EXPLICITOS[ano]:
            status, tam, erro = inep.sondar_url(url)
            achados.append({"ano": ano, "url": url if status == "ok" else None, "bytes": tam,
                            "erros": [] if status == "ok" else [f"{url}: {status} {erro or ''}"]})
        return achados
    for grupo in VARIANTES(ano):
        erros, achado = [], None
        for nome in grupo:
            for base in BASES:
                status, tam, erro = inep.sondar_url(f"{base}/{nome}")
                if status == "ok":
                    achado = {"ano": ano, "url": f"{base}/{nome}", "bytes": tam, "erros": erros}
                    break
                if status == "erro":
                    erros.append(f"{base}/{nome}: {erro}")
            if achado:
                break
        achados.append(achado or {"ano": ano, "url": None, "bytes": None, "erros": erros, "grupo": grupo[0]})
    return achados


def baixar(item: dict) -> dict:
    pasta = DESTINO / "_zips"
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / Path(item["url"]).name
    if arq.exists() and item["bytes"] and arq.stat().st_size == item["bytes"]:
        print(f"  {item['ano']}: já baixado ({arq.name})")
    else:
        parcial = arq.with_suffix(".zip.part")
        with inep.abrir(item["url"], so_um_byte=False, timeout=1800) as r, parcial.open("wb") as f:
            while bloco := r.read(1 << 20):
                f.write(bloco)
        if item["bytes"] and parcial.stat().st_size != item["bytes"]:
            parcial.unlink()
            sys.exit(f"{item['url']}: tamanho baixado difere do anunciado — download incompleto.")
        parcial.rename(arq)
        print(f"  {item['ano']}: {arq.stat().st_size / 1e6:.0f} MB → {arq}")
    h = hashlib.md5()
    with arq.open("rb") as f:
        while bloco := f.read(1 << 24):
            h.update(bloco)
    return {"ano": item["ano"], "url": item["url"], "arquivo": str(arq), "bytes": arq.stat().st_size,
            "md5": h.hexdigest(), "registrado_em": datetime.now(UTC).isoformat()}


def gravar_manifesto(linhas: list[dict]) -> None:
    manifesto = DESTINO / "_manifesto.csv"
    antigas = {}
    if manifesto.exists():
        with manifesto.open() as f:
            antigas = {r["arquivo"]: r for r in csv.DictReader(f)}
    for r in linhas:
        antigas[r["arquivo"]] = r
    campos = ["ano", "url", "arquivo", "bytes", "md5", "registrado_em"]
    with manifesto.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for chave in sorted(antigas):
            w.writerow(antigas[chave])
    print(f"Manifesto: {manifesto} ({len(antigas)} arquivos)")


def nome_legivel(info: zipfile.ZipInfo) -> str:
    """Zips do INEP gravam nomes acentuados em cp850 sem a marca UTF-8 (mesmo caso do Censo)."""
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp850")
    except UnicodeError:
        return info.filename


def primeira_linha(z: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    with z.open(info) as bruto:
        linha = bruto.readline(1 << 16)
    for cod in ("utf-8-sig", "latin-1"):
        try:
            return linha.decode(cod).rstrip("\r\n")
        except UnicodeDecodeError:
            continue
    return ""


def inventariar() -> None:
    zips = sorted((DESTINO / "_zips").glob("*.zip"))
    if not zips:
        sys.exit(f"Nenhum zip em {DESTINO / '_zips'}. Baixe antes (sem --inventario).")
    linhas = []
    for zp in zips:
        print(f"\n== {zp.name} ({zp.stat().st_size / 1e6:.0f} MB)")
        with zipfile.ZipFile(zp) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                nome = nome_legivel(info)
                cab = primeira_linha(z, info) if nome.lower().endswith((".csv", ".txt")) else ""
                sep = ";" if cab.count(";") > cab.count(",") else ","
                ncol = len(cab.split(sep)) if cab else 0
                linhas.append({"zip": zp.name, "arquivo": nome, "mb": round(info.file_size / 1e6, 1),
                               "colunas": ncol, "separador": sep if cab else "", "cabecalho": cab})
                marca = f"  {ncol} col." if ncol else ""
                print(f"  {info.file_size / 1e6:9.1f} MB  {nome}{marca}")
    saida = DESTINO / "_inventario.csv"
    with saida.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["zip", "arquivo", "mb", "colunas", "separador", "cabecalho"])
        w.writeheader()
        w.writerows(linhas)
    print(f"\nInventário: {saida} ({len(linhas)} arquivos). Cabeçalhos completos estão no CSV.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sondar", action="store_true", help="só mostra o que existe, sem baixar")
    p.add_argument("--inventario", action="store_true", help="lista o conteúdo dos zips já baixados")
    p.add_argument("--anos", help="ex.: 2019,2021,2023 (padrão: todas as edições 2011–2023)")
    p.add_argument("--url", help="link de um zip copiado do site (exige --anos com um único ano)")
    args = p.parse_args()

    if args.inventario:
        inventariar()
        return

    inep.CTX = inep.contexto_ssl()
    anos = [int(a) for a in args.anos.split(",")] if args.anos else EDICOES
    if args.url:
        if len(anos) != 1:
            sys.exit("--url exige --anos com um único ano")
        CAMINHOS_EXPLICITOS[anos[0]] = [args.url]

    itens = [i for ano in anos for i in localizar(ano)]
    print(f"{'ano':<6}{'MB':>8}  arquivo")
    for i in itens:
        if i["url"]:
            print(f"{i['ano']:<6}{(i['bytes'] or 0) / 1e6:>8.0f}  {i['url']}")
        else:
            print(f"{i['ano']:<6}{'—':>8}  não encontrado ({i.get('grupo', '')})")
            for e in i["erros"]:
                print(f"{'':16}erro de rede: {e}")
    if args.sondar:
        return
    baixados = [baixar(i) for i in itens if i["url"]]
    if baixados:
        gravar_manifesto(baixados)


if __name__ == "__main__":
    main()
