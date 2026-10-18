SHELL := /bin/bash
VENV  := .venv
PY    := $(VENV)/bin/python
DBT   := cd dbt/azupdados && DBT_PROFILES_DIR=. ../../$(VENV)/bin/dbt

.PHONY: setup up down psql bronze-censo dbt-deps dbt-build dbt-docs lint

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

bronze-censo:     ## make bronze-censo ARQ=<csv> ANO=<ano> [MD5=<arquivo md5 oficial>]
	set -a; source .env; set +a; $(PY) ingest/bronze_censo_escolar.py --arquivo $(ARQ) --ano $(ANO) $(if $(MD5),--md5-oficial $(MD5),)

dbt-deps:
	set -a; source .env; set +a; $(DBT) deps

dbt-build:        ## silver + gold + testes
	set -a; source .env; set +a; $(DBT) build

dbt-docs:
	set -a; source .env; set +a; $(DBT) docs generate

lint:
	$(VENV)/bin/ruff check ingest
