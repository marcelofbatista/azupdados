"""Download (LANDING) dos microdados do Censo Escolar (INEP): só o arquivo de escolas (microdados_ed_basica).

Baixa o zip oficial, guarda o zip e o md5 em data/landing/censo_escolar/_zips/, e extrai para
data/landing/censo_escolar/ apenas:
  - microdados_ed_basica_<ano>.csv           (o que a bronze carrega)
  - md5 oficial do CSV, se o INEP o incluir  (md5/)
  - dicionário de dados                       (dicionarios/)

O nome do zip mudou ao longo dos anos; por isso aceita --url. Sem --url, usa o padrão
dados_abertos/microdados_censo_escolar_<ano>.zip (confirmado para 2014 em out/2026).
Usa o mesmo certificado intermediário dos indicadores (make certs-inep).

Uso:
  python ingest/baixar_censo_inep.py --ano 2014
  python ingest/baixar_censo_inep.py --ano 2025 --url https://download.inep.gov.br/.../microdados_censo_escolar_2025.zip
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import zipfile
from pathlib import Path

import baixar_indicadores_inep as inep

DESTINO = Path("data/landing/censo_escolar")


def baixar(url: str, arq: Path) -> None:
    status, tam, erro = inep.sondar_url(url)
    if status != "ok":
        sys.exit(f"{url}: {status} {erro or ''} — confira o link na página de microdados do INEP")
    if arq.exists() and tam and arq.stat().st_size == tam:
        print(f"já baixado: {arq} ({tam / 1e6:.0f} MB)")
        return
    parcial = arq.with_suffix(".part")
    with inep.abrir(url, so_um_byte=False, timeout=900) as r, parcial.open("wb") as f:
        while bloco := r.read(1 << 20):
            f.write(bloco)
    if tam and parcial.stat().st_size != tam:
        parcial.unlink()
        sys.exit("download incompleto: tamanho diferente do anunciado pelo servidor")
    parcial.rename(arq)
    print(f"baixado: {arq} ({arq.stat().st_size / 1e6:.0f} MB)")


def extrair(zip_path: Path, ano: int) -> None:
    with zipfile.ZipFile(zip_path) as z:
        nomes = [n for n in z.namelist() if not n.endswith("/")]
        csv = [n for n in nomes if re.search(rf"microdados_ed_basica_{ano}\.csv$", n, re.IGNORECASE)]
        if len(csv) != 1:
            sys.exit(f"esperava 1 microdados_ed_basica_{ano}.csv no zip; achei {csv}. Conteúdo: {nomes[:30]}")
        alvos = {csv[0]: DESTINO / Path(csv[0]).name}
        for n in nomes:
            base = Path(n).name
            if "md5" in base.lower() and str(ano) in base:
                alvos[n] = DESTINO / "md5" / base
            elif "dicion" in n.lower() and base.lower().endswith((".xlsx", ".xls", ".ods", ".pdf")):
                alvos[n] = DESTINO / "dicionarios" / f"{ano}_{base}"
        for n, destino in alvos.items():
            destino.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as origem, destino.open("wb") as saida:
                shutil.copyfileobj(origem, saida, 1 << 20)
            print(f"  extraído: {destino} ({destino.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ano", type=int, required=True)
    p.add_argument("--url", help="link do zip, copiado da página de microdados do INEP")
    args = p.parse_args()

    inep.CTX = inep.contexto_ssl()
    url = args.url or f"https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_{args.ano}.zip"
    zips = DESTINO / "_zips"
    zips.mkdir(parents=True, exist_ok=True)
    arq = zips / Path(url).name
    baixar(url, arq)
    md5 = hashlib.md5(arq.read_bytes()).hexdigest()
    (zips / f"{arq.name}.md5").write_text(f"{md5}  {arq.name}\n{url}\n")
    print(f"md5 do zip: {md5}")
    extrair(arq, args.ano)
    print(f"\nPróximo passo: make bronze-censo ARQ=data/landing/censo_escolar/microdados_ed_basica_{args.ano}.csv "
          f"ANO={args.ano}  (+ MD5=<arquivo em md5/> se o INEP incluiu um)")


if __name__ == "__main__":
    main()
