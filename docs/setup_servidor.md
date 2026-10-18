# Configuração do servidor (Hetzner)

Passo a passo para subir o `azupdados` em um servidor Linux com Docker já instalado.

## 1. Pré-requisitos

```bash
df -h /                       # precisa de pelo menos 30 GB livres
docker --version && docker compose version
sudo apt update && sudo apt install -y git make python3-venv python3-pip rclone
```

## 2. Clonar e configurar

```bash
cd ~ && git clone https://github.com/marcelofbatista/azupdados.git && cd azupdados
cp .env.example .env
nano .env                     # troque POSTGRES_PASSWORD; ajuste POSTGRES_PORT se 5433 estiver ocupada
make setup                    # venv + dbt + dependências
make up                       # PostgreSQL do azupdados (só em 127.0.0.1)
```

Confira se a porta está livre antes do `make up`: `ss -ltnp | grep -E '5432|5433'`.

## 3. Conectar o rclone ao Google Drive

O servidor não tem navegador, então a autorização é feita no notebook:

1. No **notebook**, com o rclone instalado: `rclone authorize "drive"` → faça login na conta do Google que tem os
   microdados → copie o token que aparecer no terminal.
2. No **servidor**: `rclone config` → `n` (novo remote) → nome `gdrive` → tipo `drive` → deixe `client_id` e
   `client_secret` vazios → escopo `2` (somente leitura) → `Edit advanced config? n` →
   `Use web browser to automatically authenticate? n` → cole o token → `Configure this as a Shared Drive? n`
   (responda `y` só se as pastas estiverem em um Drive compartilhado).
3. Teste: `rclone lsd "gdrive,root_folder_id=14PSE2XhXsEZawGeiV1xjm9Joj-Brtgrk:"`

## 4. Baixar os microdados e carregar a bronze

```bash
./ingest/sync_drive.sh        # ~10 GB; pode levar um tempo
ls -lh data/landing/censo_escolar

make bronze-censo ARQ=data/landing/censo_escolar/microdados_ed_basica_2024.csv ANO=2024 \
     MD5=data/landing/censo_escolar/md5/md5_microdados_ed_basica_2024.txt

# demais anos (sem md5 oficial disponível no Drive)
for ano in 2015 2016 2017 2018 2019 2020 2021 2022 2023; do
  arq=$(ls data/landing/censo_escolar/microdados_ed_basica_${ano}.* | head -1)
  make bronze-censo ARQ="$arq" ANO=$ano
done
```

## 5. Rodar o dbt

```bash
make dbt-deps
make dbt-build                # silver + gold + todos os testes
```

## Acesso ao banco a partir do notebook

O PostgreSQL só escuta em `127.0.0.1` no servidor. Para usar pgAdmin, DBeaver ou Power BI no notebook,
abra um túnel SSH e conecte em `localhost:5433`:

```bash
ssh -N -L 5433:127.0.0.1:5433 usuario@IP_DO_SERVIDOR
```
