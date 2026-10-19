"""Extração BRONZE do SEDAP+ (INEP): matrículas da educação especial por tipo, UF e dependência.

O SEDAP+ aplica privacidade diferencial: cada número volta com ruído e com intervalo de confiança.
Por isso a consulta é feita no grão GROSSO (UF × dependência × ano), onde o ruído é desprezível,
e a resposta da API é guardada INTEIRA (com as estatísticas de privacidade) na camada bronze.

Credenciais (aba Integração do SEDAP+) vêm do ambiente, nunca do código:
  SEDAP_TOKEN, SEDAP_PROCESS_UUID, SEDAP_PROFILE_ID

Uso:
  python ingest/sedap_tipo_deficiencia.py --anos 2024 --mostrar-sql   # só imprime as consultas
  python ingest/sedap_tipo_deficiencia.py --anos 2024                 # valida um ano
  python ingest/sedap_tipo_deficiencia.py --anos 2015-2024            # série completa

Cada consulta consome orçamento de privacidade do projeto no SEDAP+. Não rode em loop à toa.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ENDPOINT = "https://backend.rpinep2.prd.app.rnp.br/ide/send-process/{uuid}"
DESTINO = Path("data/landing/sedap/tipo_deficiencia")

# Indicadores por tipo na base de matrícula. CONFERIR no dicionário do ano antes da série completa:
# nomes podem variar entre edições (a API devolve 422 se a coluna não existir).
TIPOS = {
    "cegueira": "IN_CEGUEIRA",
    "baixa_visao": "IN_BAIXA_VISAO",
    "surdez": "IN_SURDEZ",
    "def_auditiva": "IN_DEF_AUDITIVA",
    "surdocegueira": "IN_SURDOCEGUEIRA",
    "def_fisica": "IN_DEF_FISICA",
    "def_intelectual": "IN_DEF_INTELECTUAL",
    "def_multipla": "IN_DEF_MULTIPLA",
    "autismo_tea": "IN_AUTISMO",
    "superdotacao": "IN_SUPERDOTACAO",
}


FILTRO = "IN_ESPECIAL_EXCLUSIVA IS NOT NULL AND TP_ETAPA_ENSINO IS NOT NULL"
# Matrículas de AEE e de turmas sem etapa (atividade complementar, itinerário em turma própria) são
# registros extras do mesmo aluno; o Censo aberto e a Sinopse contam só a escolarização (armadilha 09).

# Métrica → condição extra no WHERE. Cada métrica é UMA consulta com COUNT: nas bases 2015–2023,
# SUM(CASE WHEN ...) volta com ruído enorme (desvio médio de 48% a 109% por grupo), e COUNT com
# filtro fica a ~1% do Censo aberto.
METRICAS = {"total_matriculas": None, "total_educacao_especial": "IN_NECESSIDADE_ESPECIAL = 1"}
METRICAS.update({nome: f"{col} = 1" for nome, col in TIPOS.items()})


def montar_sql(ano: int, metrica: str) -> str:
    extra = METRICAS[metrica]
    where = FILTRO + (f" AND {extra}" if extra else "")
    return (
        f"SELECT CO_UF, TP_DEPENDENCIA, COUNT(ID_MATRICULA) AS {metrica}\n"
        f"FROM raw.BAS_MATRICULA_{ano}\n"
        f"WHERE {where}\n"
        f"GROUP BY CO_UF, TP_DEPENDENCIA"
    )


def consultar(sql: str) -> dict:
    try:
        token = os.environ["SEDAP_TOKEN"]
        uuid = os.environ["SEDAP_PROCESS_UUID"]
        perfil = os.environ["SEDAP_PROFILE_ID"]
    except KeyError as e:
        sys.exit(f"Variável de ambiente ausente: {e}. Defina-a no .env (nunca no código).")
    req = urllib.request.Request(
        ENDPOINT.format(uuid=uuid),
        data=json.dumps({"content": sql}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "profile-id": perfil,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            # Atenção: o SEDAP+ responde 201 (não 200) quando a consulta dá certo.
            if resp.status not in (200, 201):
                sys.exit(f"HTTP {resp.status}")
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='ignore')[:500]}")


def anos_de(texto: str) -> list[int]:
    if "-" in texto:
        ini, fim = (int(x) for x in texto.split("-"))
        return list(range(ini, fim + 1))
    return [int(x) for x in texto.split(",")]


def extrair_ano(ano: int, refazer: bool) -> Path:
    """Uma consulta por métrica, com cache: uma métrica já paga nunca é consultada de novo."""
    partes = DESTINO / "_partes"
    partes.mkdir(parents=True, exist_ok=True)
    linhas: dict[tuple, dict] = {}
    estatisticas, consultas = [], []
    for metrica in METRICAS:
        cache = partes / f"{ano}_{metrica}.json"
        sql = montar_sql(ano, metrica)
        if cache.exists() and not refazer:
            resp = json.loads(cache.read_text())
        else:
            print(f"[{ano}] {metrica} ...", flush=True)
            resp = consultar(sql)
            cache.write_text(json.dumps(resp, ensure_ascii=False))
            time.sleep(2)
        consultas.append(sql)
        for row in resp["rows"]:
            chave = (str(row["CO_UF"]), str(row["TP_DEPENDENCIA"]))
            linhas.setdefault(chave, {"CO_UF": chave[0], "TP_DEPENDENCIA": chave[1]})[metrica] = row[metrica]
        stats = resp.get("bqconnector_statistics")
        if stats is not None:
            estatisticas.append(stats)
    registro = {
        "ano": ano,
        "metodo": "count_por_metrica",
        "consulta": "\n;\n".join(consultas),
        "excluiu_aee": True,
        "extraido_em": datetime.now(UTC).isoformat(),
        # mesmo formato de resposta de uma consulta única, para a bronze não mudar
        "resposta": {"success": True, "bqconnector_statistics": estatisticas, "rows": list(linhas.values())},
    }
    arq = DESTINO / f"tipo_deficiencia_{ano}.json"
    arq.write_text(json.dumps(registro, ensure_ascii=False, indent=1))
    return arq


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", required=True, help="ex.: 2024 | 2015-2024 | 2019,2021")
    p.add_argument("--mostrar-sql", action="store_true", help="só imprime as consultas, não chama a API")
    p.add_argument("--refazer", action="store_true", help="ignora o cache e consulta de novo (gasta orçamento)")
    args = p.parse_args()

    anos = anos_de(args.anos)
    if args.mostrar_sql:
        for metrica in METRICAS:
            print(f"-- {anos[0]} / {metrica}\n{montar_sql(anos[0], metrica)}\n")
        return
    DESTINO.mkdir(parents=True, exist_ok=True)
    print(f"{len(anos)} ano(s) × {len(METRICAS)} métricas = até {len(anos) * len(METRICAS)} consultas (cache evita repetir)")
    for ano in anos:
        arq = extrair_ano(ano, args.refazer)
        print(f"[{ano}] → {arq}")


if __name__ == "__main__":
    main()
