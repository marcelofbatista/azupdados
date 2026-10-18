#!/usr/bin/env bash
# Copia os microdados oficiais do Google Drive para data/landing/ usando rclone.
# Só arquivos oficiais do INEP entram. Recortes e scripts de outros projetos ficam de fora.
#
# Pré-requisito: um remote rclone chamado "gdrive" (ver docs/setup_servidor.md).
set -euo pipefail

REMOTE="${REMOTE:-gdrive}"
DESTINO="${DESTINO:-data/landing}"

# IDs das pastas no Drive (microdados oficiais)
CENSO_CSV="14PSE2XhXsEZawGeiV1xjm9Joj-Brtgrk"      # microdados_ed_basica_<ano>.csv
CENSO_DIC="1FRX0pjA3tZN1x2MBtPc8s2r9yk-uUae1"      # dicionários do Censo
CENSO_2024="1HBPnDHOiDxnUELlz_27WjyPOl3mtgd9X"     # inclui o md5 oficial de 2024
SAEB="1qGY08ZW02v2IxHWsNZHDwMX5ucQFJ61d"           # microdados_saeb_<ano>.zip
IDEB="1YLu25NCraU4GkVSpV16WaSUFr526clN_"           # divulgações oficiais do IDEB

OPTS=(--progress --transfers 4 --checksum)
INCLUIR_SAEB="${INCLUIR_SAEB:-0}"   # SAEB ocupa ~5 GB zipado; só baixe quando for processar

# --drive-root-folder-id funciona em qualquer versão do rclone (inclusive a 1.53 do apt)
copiar() { local pasta="$1" destino="$2"; shift 2
  rclone copy "${REMOTE}:" "${destino}" --drive-root-folder-id "${pasta}" "${OPTS[@]}" "$@"; }

# Proteção de disco: aborta se sobrar menos de 15 GB livres no destino
mkdir -p "${DESTINO}"
LIVRE_GB=$(df -BG --output=avail "${DESTINO}" | tail -1 | tr -dc '0-9')
if [ "${LIVRE_GB}" -lt 15 ]; then
  echo "Apenas ${LIVRE_GB} GB livres em ${DESTINO}. Abortando para não lotar o disco."; exit 1
fi

echo ">> Censo Escolar (CSVs)"
copiar "${CENSO_CSV}" "${DESTINO}/censo_escolar" --include "microdados_ed_basica_*.{csv,CSV}"

echo ">> md5 oficial"
copiar "${CENSO_2024}" "${DESTINO}/censo_escolar/md5" --include "md5_*.txt"

echo ">> Dicionários do Censo"
copiar "${CENSO_DIC}" "${DESTINO}/censo_escolar/dicionarios"

if [ "${INCLUIR_SAEB}" = "1" ]; then
  echo ">> SAEB (somente microdados oficiais)"
  copiar "${SAEB}" "${DESTINO}/saeb" --include "microdados_saeb_*.zip" --include "Dicionario_Saeb_*.xlsx" --max-depth 1
else
  echo ">> SAEB pulado (rode com INCLUIR_SAEB=1 quando for processar)"
fi

echo ">> IDEB (somente divulgações oficiais)"
copiar "${IDEB}" "${DESTINO}/ideb" --include "*divulgacao*.{zip,xlsx}" --include "nota_informativa_*.pdf" --max-depth 1

echo ">> Concluído"
du -sh "${DESTINO}"/*
