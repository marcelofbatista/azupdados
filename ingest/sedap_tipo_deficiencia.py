"""Extração BRONZE do SEDAP+ (INEP): matrículas da educação especial por tipo, UF e dependência.

O SEDAP+ aplica privacidade diferencial: cada número volta com ruído e com intervalo de confiança.
Por isso a consulta é feita no grão GROSSO (UF × dependência × ano), onde o ruído é desprezível,
e a resposta da API é guardada INTEIRA (com as estatísticas de privacidade) na camada bronze.

Credenciais (aba Integração do SEDAP+) vêm do ambiente, nunca do código:
  SEDAP_TOKEN, SEDAP_PROCESS_UUID, SEDAP_PROFILE_ID

Uso:
  python ingest/sedap_tipo_deficiencia.py --anos 2024 --mostrar-sql   # só imprime a consulta
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


def montar_sql(ano: int, excluir_aee: bool) -> str:
    somas = ",\n  ".join(
        f"SUM(CASE WHEN {col} = 1 THEN 1 ELSE 0 END) AS {nome}" for nome, col in TIPOS.items()
    )
    # Matrículas de AEE (atendimento no contraturno) são registros à parte do mesmo aluno.
    # Incluí-las conta o estudante duas vezes; a Sinopse do INEP conta só a escolarização.
    filtro = "WHERE IN_ESPECIAL_EXCLUSIVA IS NOT NULL" if excluir_aee else ""
    return (
        f"SELECT CO_UF, TP_DEPENDENCIA,\n"
        f"  COUNT(ID_MATRICULA) AS total_matriculas,\n"
        f"  SUM(CASE WHEN IN_NECESSIDADE_ESPECIAL = 1 THEN 1 ELSE 0 END) AS total_educacao_especial,\n"
        f"  {somas}\n"
        f"FROM raw.BAS_MATRICULA_{ano}\n"
        f"{filtro}\n"
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


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", required=True, help="ex.: 2024 | 2015-2024 | 2019,2021")
    p.add_argument("--incluir-aee", action="store_true", help="não excluir matrículas de AEE")
    p.add_argument("--mostrar-sql", action="store_true", help="só imprime a consulta, não chama a API")
    args = p.parse_args()

    DESTINO.mkdir(parents=True, exist_ok=True)
    for ano in anos_de(args.anos):
        sql = montar_sql(ano, excluir_aee=not args.incluir_aee)
        if args.mostrar_sql:
            print(f"-- {ano}\n{sql}\n")
            continue
        print(f"[{ano}] consultando SEDAP+ ...", flush=True)
        resposta = consultar(sql)
        registro = {
            "ano": ano,
            "consulta": sql,
            "excluiu_aee": not args.incluir_aee,
            "extraido_em": datetime.now(UTC).isoformat(),
            "resposta": resposta,  # inclui linhas e estatísticas de privacidade (ruído, IC 95%)
        }
        arq = DESTINO / f"tipo_deficiencia_{ano}.json"
        arq.write_text(json.dumps(registro, ensure_ascii=False, indent=1))
        print(f"[{ano}] {len(resposta.get('rows', []))} grupos → {arq}")
        time.sleep(2)


if __name__ == "__main__":
    main()
