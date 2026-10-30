SHELL := /bin/bash
VENV  := .venv
PY    := $(VENV)/bin/python
DBT_THREADS ?= 2
DBT   := cd dbt/azupdados && DBT_PROFILES_DIR=. ../../$(VENV)/bin/dbt

.PHONY: setup up down psql sql bronze-censo censo-baixar sedap-extrair bronze-sedap bronze-ideb certs-inep indicadores-sondar indicadores-baixar bronze-indicadores saeb-sondar saeb-baixar saeb-inventario spark-setup saeb-dicionario saeb-bronze saeb-verificar-escola saeb-silver saeb-agregar bronze-saeb-resultados dbt-deps dbt-build dbt-build-full dbt-docs lint

setup:            ## cria o venv e instala dependências
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	@test -f dbt/azupdados/profiles.yml || cp dbt/azupdados/profiles.yml.example dbt/azupdados/profiles.yml

up:               ## sobe o PostgreSQL
	docker compose up -d
	docker compose ps

down:
	docker compose down

psql:             ## abre o psql dentro do container
	set -a; source .env; set +a; docker exec -it azupdados-postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB

sql:              ## roda SQL vindo da entrada padrão (sem terminal):  make sql <<'SQL' ... SQL
	set -a; source .env; set +a; docker exec -i azupdados-postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB -P pager=off

bronze-censo:     ## make bronze-censo ARQ=<csv> ANO=<ano> [MD5=<arquivo md5 oficial>]
	set -a; source .env; set +a; $(PY) ingest/bronze_censo_escolar.py --arquivo $(ARQ) --ano $(ANO) $(if $(MD5),--md5-oficial $(MD5),)

censo-baixar:     ## baixa o zip do Censo Escolar do INEP e extrai o CSV de escolas  [ANO=2014 URL=<link, se o padrão falhar>]
	$(PY) ingest/baixar_censo_inep.py --ano $(ANO) $(if $(URL),--url $(URL))

sedap-extrair:    ## make sedap-extrair ANOS=2015-2024 (consome orçamento de privacidade do SEDAP+)
	set -a; source .env; set +a; $(PY) ingest/sedap_tipo_deficiencia.py --anos $(ANOS)

bronze-sedap:     ## carrega na bronze os JSON do SEDAP+ já extraídos
	set -a; source .env; set +a; $(PY) ingest/bronze_sedap.py

bronze-ideb:      ## carrega na bronze as planilhas de divulgação do IDEB 2025 (série desde 2005)
	set -a; source .env; set +a; $(PY) ingest/bronze_ideb.py

CERT_INEP := data/certs/rnp_icpedu_gr46_ov_tls_ca_2025.pem
AIA_INEP  := http://secure.globalsign.com/cacert/rnpicpedugr46ovtlsca2025.crt

certs-inep:       ## baixa o certificado intermediário que o download.inep.gov.br não envia (e confere a cadeia)
	mkdir -p data/certs
	curl -sS -o /tmp/rnp_inter.crt $(AIA_INEP)
	openssl x509 -inform DER -in /tmp/rnp_inter.crt -out $(CERT_INEP) 2>/dev/null || cp /tmp/rnp_inter.crt $(CERT_INEP)
	openssl x509 -in $(CERT_INEP) -noout -subject -issuer -fingerprint -sha256
	openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt $(CERT_INEP)

indicadores-sondar: ## lista os arquivos por escola que existem no INEP (sem baixar)  [IND=TDI,REND ANOS=2015-2025]
	$(PY) ingest/baixar_indicadores_inep.py --sondar $(if $(IND),--indicadores $(IND)) $(if $(ANOS),--anos $(ANOS))

indicadores-baixar: ## baixa os indicadores por escola para data/landing/indicadores (+ manifesto com md5)
	$(PY) ingest/baixar_indicadores_inep.py $(if $(IND),--indicadores $(IND)) $(if $(ANOS),--anos $(ANOS))

bronze-indicadores: ## carrega na bronze os indicadores por escola  [IND=TDI ANOS=2024,2025 SO_CAB=1]
	set -a; source .env; set +a; $(PY) ingest/bronze_indicadores.py $(if $(IND),--indicadores $(IND)) $(if $(ANOS),--anos $(ANOS)) $(if $(SO_CAB),--so-cabecalhos)

saeb-sondar:      ## lista os zips de microdados do SAEB que existem no INEP (sem baixar)  [ANOS=2019,2021,2023]
	$(PY) ingest/baixar_saeb_inep.py --sondar $(if $(ANOS),--anos $(ANOS))

saeb-baixar:      ## baixa os zips do SAEB para data/landing/saeb/_zips (+ manifesto com md5)  [ANOS=... URL=<link>]
	$(PY) ingest/baixar_saeb_inep.py $(if $(ANOS),--anos $(ANOS)) $(if $(URL),--url $(URL))

saeb-inventario:  ## lista o conteúdo dos zips do SAEB sem extrair (arquivos, tamanhos, cabeçalhos)
	$(PY) ingest/baixar_saeb_inep.py --inventario

spark-setup:      ## instala o PySpark no venv (o Java vem antes: sudo apt-get install -y openjdk-17-jre-headless)
	@command -v java >/dev/null || (echo "Falta o Java: sudo apt-get install -y openjdk-17-jre-headless" && exit 1)
	java -version 2>&1 | head -1
	$(VENV)/bin/pip install -r requirements-spark.txt

saeb-dicionario:  ## mostra no dicionário oficial onde estão sexo, cor/raça e INSE em cada edição  [TERMOS="..."]
	$(PY) ingest/saeb_dicionario.py $(if $(TERMOS),--termos "$(TERMOS)")

saeb-bronze:      ## SAEB por aluno: CSV oficial → Parquet com PySpark  [ANOS=2019,2021,2023 ARQ=5EF]
	set -a; source .env; set +a; PYTHONPATH=spark $(PY) spark/bronze_saeb.py --anos $(ANOS) $(if $(ARQ),--arquivos $(ARQ))

saeb-verificar-escola: ## o ID_ESCOLA do SAEB é o código real? cruza com gold.dim_escola (escola e município)
	set -a; source .env; set +a; PYTHONPATH=spark $(PY) spark/verificar_escola_saeb.py

saeb-silver:      ## SAEB: edições harmonizadas, aluno × disciplina, perfil decodificado (Parquet)  [ANOS=2019,2021,2023]
	PYTHONPATH=spark $(PY) spark/silver_saeb.py --anos $(ANOS)

saeb-agregar:     ## SAEB: agrega com PySpark e carrega silver.saeb_agregado no Postgres  [ANOS=2019,2021,2023]
	set -a; source .env; set +a; PYTHONPATH=spark $(PY) spark/agregar_saeb.py --anos $(ANOS)

bronze-saeb-resultados: ## carrega as médias oficiais do SAEB (TS_BRASIL, TS_UF) — gabarito da reconciliação
	set -a; source .env; set +a; $(PY) ingest/bronze_saeb_resultados.py

dbt-deps:
	set -a; source .env; set +a; $(DBT) deps

dbt-build:        ## silver + gold + testes  (só uma parte: make dbt-build SEL='+fato_ideb_escola_ano')
	set -a; source .env; set +a; $(DBT) build --threads $(DBT_THREADS) $(if $(SEL),--select $(SEL),)

dbt-build-full:   ## recria seeds e tabelas do zero (necessário quando muda a estrutura de uma seed)
	set -a; source .env; set +a; $(DBT) build --full-refresh --threads $(DBT_THREADS)

dbt-docs:
	set -a; source .env; set +a; $(DBT) docs generate

lint:
	$(VENV)/bin/ruff check ingest
