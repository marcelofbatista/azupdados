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

echo ">> Censo Escolar (CSVs)"
rclone copy "${REMOTE},root_folder_id=${CENSO_CSV}:" "${DESTINO}/censo_escolar" "${OPTS[@]}" \
  --include "microdados_ed_basica_*.{csv,CSV}"

echo ">> md5 oficial"
rclone copy "${REMOTE},root_folder_id=${CENSO_2024}:" "${DESTINO}/censo_escolar/md5" "${OPTS[@]}" \
  --include "md5_*.txt"

echo ">> Dicionários do Censo"
rclone copy "${REMOTE},root_folder_id=${CENSO_DIC}:" "${DESTINO}/censo_escolar/dicionarios" "${OPTS[@]}"

echo ">> SAEB (somente microdados oficiais)"
rclone copy "${REMOTE},root_folder_id=${SAEB}:" "${DESTINO}/saeb" "${OPTS[@]}" \
  --include "microdados_saeb_*.zip" --include "Dicionario_Saeb_*.xlsx" --max-depth 1

echo ">> IDEB (somente divulgações oficiais)"
rclone copy "${REMOTE},root_folder_id=${IDEB}:" "${DESTINO}/ideb" "${OPTS[@]}" \
  --include "*divulgacao*.{zip,xlsx}" --include "nota_informativa_*.pdf" --max-depth 1

echo ">> Concluído"
du -sh "${DESTINO}"/*
