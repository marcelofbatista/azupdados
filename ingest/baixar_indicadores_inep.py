"""Download (LANDING) dos indicadores educacionais do INEP por escola.

Indicadores (sigla → pasta em data/landing/indicadores/):
  REND  taxas de rendimento (aprovação, reprovação, abandono)     rendimento/
  TDI   taxa de distorção idade-série                             tdi/
  ATU   média de alunos por turma                                 atu/
  HAD   média de horas-aula diária                                had/
  AFD   adequação da formação docente                             afd/
  IRD   regularidade do corpo docente                             ird/
  IED   esforço docente                                           ied/
  ICG   complexidade de gestão da escola                          icg/
  INSE  nível socioeconômico (edições do SAEB)                    inse/

O INEP muda a grafia dos nomes ao longo dos anos e às vezes publica um ano na pasta do ano seguinte.
Por isso, para cada indicador × ano, o script testa uma lista CURTA e EXPLÍCITA de variantes (abaixo) e
usa a primeira que existir. Nada é adivinhado fora dessa lista: ano não encontrado aparece no relatório,
e o link certo deve ser copiado do site e acrescentado em VARIANTES.

Certificado: o servidor download.inep.gov.br não envia o certificado intermediário (RNP ICPEdu, emitido
pela GlobalSign). O navegador busca sozinho; o Python não. A verificação HTTPS continua LIGADA: o script
só acrescenta esse intermediário às autoridades padrão. Gere o arquivo uma vez com `make certs-inep`.

Uso:
  python ingest/baixar_indicadores_inep.py --sondar                    # só lista o que existe (1 byte por arquivo)
  python ingest/baixar_indicadores_inep.py                             # baixa tudo o que existir
  python ingest/baixar_indicadores_inep.py --indicadores TDI,REND --anos 2019-2025
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

BASE = "https://download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais"
DESTINO = Path("data/landing/indicadores")
CERT_INTERMEDIARIO = Path(os.environ.get("INEP_CAFILE", "data/certs/rnp_icpedu_gr46_ov_tls_ca_2025.pem"))
UA = "Mozilla/5.0 (azupdados; +https://github.com/marcelofbatista/azupdados)"

PASTA = {"REND": "rendimento", "TDI": "tdi", "ATU": "atu", "HAD": "had", "AFD": "afd",
         "IRD": "ird", "IED": "ied", "ICG": "icg", "INSE": "inse"}


def VARIANTES(sig: str, ano: int) -> list[str]:
    """Caminhos candidatos, relativos a BASE, na ordem de preferência.

    Confirmados no site (out/2026): <SIG>_<ano>_ESCOLAS.zip (2024–2025), tx_rend_escolas_<ano>.zip (2024–2025),
    <ano>/nivel_socioeconomico/INSE_<ano>_escolas.xlsx (2021, 2023). As demais são grafias que o INEP já usou.
    """
    if sig == "INSE":
        nomes = [f"nivel_socioeconomico/INSE_{ano}_escolas.xlsx", f"nivel_socioeconomico/INSE_{ano}_ESCOLAS.xlsx",
                 f"nivel_socioeconomico/INSE_{ano}_escolas.zip", f"INSE_{ano}_escolas.xlsx",
                 f"INSE_{ano}_escolas.zip", f"nivel_socioeconomico/INSE_{ano}.zip", f"INSE_{ano}.zip"]
    elif sig == "REND":
        nomes = [f"tx_rend_escolas_{ano}.zip", f"TX_REND_ESCOLAS_{ano}.zip", f"tx_rend_{ano}_escolas.zip",
                 f"TX_REND_{ano}_ESCOLAS.zip", f"tx_rend_escolas_{ano}.rar"]
    else:
        nomes = [f"{sig}_{ano}_ESCOLAS.zip", f"{sig.lower()}_{ano}_escolas.zip", f"{sig}_ESCOLAS_{ano}.zip",
                 f"{sig.lower()}_escolas_{ano}.zip", f"{sig}_{ano}_ESCOLAS.rar", f"{sig.lower()}_escolas_{ano}.rar"]
    return [f"{pasta}/{n}" for pasta in (ano, ano + 1) for n in nomes]


# Anos fora do padrão de nome, copiados do site do INEP (out/2026). Em 2015 cada indicador tinha subpasta
# temática; o INSE 2011–2013 é um arquivo único (registrado como 2013). INSE 2013 e 2015 usam metodologia
# anterior, NÃO comparável com 2019+ (aviso do INEP): a silver marca isso, a landing guarda o original.
CAMINHOS_EXPLICITOS = {
    ("TDI", 2015): "2015/distorcao_idade_serie/tdi_escolas_2015.zip",
    ("REND", 2015): "2015/taxa_rendimento/tx_rendimento_escolas_2015.zip",
    ("REND", 2016): "2016/TAXA_REND_2016_ESCOLAS.zip",
    ("REND", 2017): "2017/TAXA_REND_2017_ESCOLAS.zip",
    ("ATU", 2015): "2015/alunos_turma/media_alunos_turma_escolas_2015.zip",
    ("HAD", 2015): "2015/horas_aula_diaria/horas_aula_escolas_2015.zip",
    ("AFD", 2015): "2015/adequacao_formacao_docente/adequacao_formacao_docente_escolas_2015.zip",
    ("IRD", 2015): "2015/regularidade_corpo_docente/regularidade_corpo_docente_escolas_2015.zip",
    ("IED", 2015): "2015/esforco_docente/esforco_docente_escolas_2015.zip",
    ("ICG", 2015): "2015/complexidade_gestao_escola/complexidade_gestao_escola_escolas_2015.zip",
    ("INSE", 2015): "2015/nivel_socioeconomico/Indicador_Inse_2015.zip",
    ("INSE", 2013): "2011_2013/nivel_socioeconomico/Indicador_INSE_por_Escola.zip",
}

ANOS_PADRAO = {"INSE": [2013, 2015, 2019, 2021, 2023]}
ANOS_GERAL = list(range(2015, 2026))  # série do projeto; antes de 2015 o INEP não publica por escola neste formato


def contexto_ssl() -> ssl.SSLContext:
    if not CERT_INTERMEDIARIO.exists():
        sys.exit(f"Falta {CERT_INTERMEDIARIO}. Rode `make certs-inep` uma vez (baixa o intermediário da RNP).")
    ctx = ssl.create_default_context()          # autoridades do sistema, verificação ligada
    ctx.load_verify_locations(cafile=str(CERT_INTERMEDIARIO))
    return ctx


CTX: ssl.SSLContext | None = None


def abrir(url: str, so_um_byte: bool, timeout: int = 60):
    headers = {"User-Agent": UA}
    if so_um_byte:
        headers["Range"] = "bytes=0-0"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), context=CTX, timeout=timeout)


def sondar_url(url: str) -> tuple[str, int | None, str | None]:
    """(status, tamanho, erro). status: 'ok' | '404' | 'erro'."""
    for tentativa in range(3):
        try:
            with abrir(url, so_um_byte=True) as r:
                total = (r.headers.get("Content-Range") or "").split("/")[-1]
                tam = int(total) if total.isdigit() else int(r.headers.get("Content-Length") or 0) or None
                return "ok", tam, None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "404", None, None
            erro = f"HTTP {e.code}"
        except OSError as e:  # rede, TLS (URLError é OSError): mostrar, nunca esconder como "não encontrado"
            erro = f"{type(e).__name__}: {e}"
        time.sleep(2 * (tentativa + 1))
    return "erro", None, erro


def localizar(sig: str, ano: int) -> dict:
    erros = []
    candidatos = VARIANTES(sig, ano)
    if (sig, ano) in CAMINHOS_EXPLICITOS:
        candidatos = [CAMINHOS_EXPLICITOS[(sig, ano)], *candidatos]
    for caminho in candidatos:
        status, tam, erro = sondar_url(f"{BASE}/{caminho}")
        if status == "ok":
            return {"sig": sig, "ano": ano, "caminho": caminho, "bytes": tam, "erros": erros}
        if status == "erro":
            erros.append(f"{caminho}: {erro}")
    return {"sig": sig, "ano": ano, "caminho": None, "bytes": None, "erros": erros}


def baixar(item: dict) -> dict:
    url = f"{BASE}/{item['caminho']}"
    pasta = DESTINO / PASTA[item["sig"]]
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / Path(item["caminho"]).name
    if arq.exists() and item["bytes"] and arq.stat().st_size == item["bytes"]:
        print(f"  {item['sig']} {item['ano']}: já baixado ({arq.name})")
    else:
        parcial = arq.with_suffix(arq.suffix + ".part")
        with abrir(url, so_um_byte=False, timeout=600) as r, parcial.open("wb") as f:
            while bloco := r.read(1 << 20):
                f.write(bloco)
        if item["bytes"] and parcial.stat().st_size != item["bytes"]:
            parcial.unlink()
            sys.exit(f"{url}: tamanho baixado difere do anunciado pelo servidor — download incompleto.")
        parcial.rename(arq)
        print(f"  {item['sig']} {item['ano']}: {arq.stat().st_size / 1e6:.1f} MB → {arq}")
    md5 = hashlib.md5(arq.read_bytes()).hexdigest()
    return {"indicador": item["sig"], "ano": item["ano"], "url": url, "arquivo": str(arq),
            "bytes": arq.stat().st_size, "md5": md5, "registrado_em": datetime.now(UTC).isoformat()}


def gravar_manifesto(linhas: list[dict]) -> None:
    manifesto = DESTINO / "_manifesto.csv"
    antigas = {}
    if manifesto.exists():
        with manifesto.open() as f:
            antigas = {(r["indicador"], r["ano"]): r for r in csv.DictReader(f)}
    for r in linhas:
        antigas[(r["indicador"], str(r["ano"]))] = r
    campos = ["indicador", "ano", "url", "arquivo", "bytes", "md5", "registrado_em"]
    with manifesto.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for chave in sorted(antigas):
            w.writerow(antigas[chave])
    print(f"Manifesto: {manifesto} ({len(antigas)} arquivos)")


def anos_de(texto: str | None, sig: str) -> list[int]:
    padrao = ANOS_PADRAO.get(sig, ANOS_GERAL)
    if not texto:
        return padrao
    if "-" in texto:
        ini, fim = (int(x) for x in texto.split("-"))
        pedidos = set(range(ini, fim + 1))
    else:
        pedidos = {int(x) for x in texto.split(",")}
    return [a for a in padrao if a in pedidos] if sig == "INSE" else sorted(pedidos)


def main() -> None:
    global CTX
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sondar", action="store_true", help="só mostra o que existe, sem baixar")
    p.add_argument("--indicadores", default=",".join(PASTA), help="ex.: TDI,REND (padrão: todos)")
    p.add_argument("--anos", help="ex.: 2015-2025 | 2019,2021 (padrão: 2015–2025; INSE: 2013, 2015, 2019, 2021, 2023)")
    args = p.parse_args()

    CTX = contexto_ssl()
    sigs = [s.strip().upper() for s in args.indicadores.split(",")]
    if desconhecidos := [s for s in sigs if s not in PASTA]:
        sys.exit(f"Indicador desconhecido: {desconhecidos}. Válidos: {list(PASTA)}")
    tarefas = [(s, a) for s in sigs for a in anos_de(args.anos, s)]

    with ThreadPoolExecutor(6) as ex:
        achados = list(ex.map(lambda t: localizar(*t), tarefas))

    atual, total = None, 0
    for it in achados:
        if it["sig"] != atual:
            atual = it["sig"]
            print(f"\n== {atual}")
        if it["caminho"]:
            total += it["bytes"] or 0
            print(f"  {it['ano']}  {(it['bytes'] or 0) / 1e6:7.1f} MB  {it['caminho']}")
        else:
            print(f"  {it['ano']}  -- não encontrado nas variantes conhecidas")
        for e in it["erros"]:
            print(f"        ERRO {e}")
    encontrados = [it for it in achados if it["caminho"]]
    print(f"\n{len(encontrados)} de {len(achados)} arquivos encontrados, {total / 1e9:.2f} GB no total")
    if any(it["erros"] for it in achados):
        print("Há erros de rede/TLS acima: o ano pode existir. Corrija antes de concluir que falta.")
    if args.sondar:
        return

    linhas = [baixar(it) for it in encontrados]  # sequencial: gentil com o servidor do INEP
    gravar_manifesto(linhas)


if __name__ == "__main__":
    main()
