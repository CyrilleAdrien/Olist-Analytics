# Olist Analytics: entry points for the whole pipeline.
# `make all` rebuilds the warehouse from scratch: up -> ingest -> build.

-include .env
DBT_DOCS_PORT ?= 8080

COMPOSE := docker compose
RUN     := $(COMPOSE) run --rm pipeline
RUN_DBT := $(COMPOSE) run --rm --workdir /app/dbt pipeline

.DEFAULT_GOAL := help
.PHONY: help up ingest build docs all down clean lint test

help: ## List the available commands
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(firstword $(MAKEFILE_LIST)) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

.env:
	@cp .env.example .env
	@echo "Created .env from .env.example"

up: .env ## Start the PostgreSQL warehouse
	$(COMPOSE) up -d --wait warehouse

ingest: .env ## Load the Olist CSV files into the raw schema
	$(RUN) python ingestion/load_raw.py

build: .env ## Run dbt deps then dbt build (models + tests)
	$(RUN_DBT) sh -c "dbt deps && dbt build"

docs: .env ## Serve the dbt documentation on http://localhost:8080
	$(COMPOSE) --profile docs up -d docs
	@echo "dbt docs: http://localhost:$(DBT_DOCS_PORT)"

all: up ingest build ## Chain up, ingest and build

down: ## Stop every service
	$(COMPOSE) --profile pipeline --profile docs down

clean: ## Stop every service and delete the warehouse volume
	$(COMPOSE) --profile pipeline --profile docs down --volumes

lint: ## Run every pre-commit hook on the whole repository
	pre-commit run --all-files

test: .env ## Run the ingestion unit tests
	$(RUN) python -m pytest ingestion/tests
