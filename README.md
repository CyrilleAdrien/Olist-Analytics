# Olist Analytics

[![CI](https://github.com/CyrilleAdrien/Olist-Analytics/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/CyrilleAdrien/Olist-Analytics/actions/workflows/ci.yml)

Containerised analytics pipeline on the
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce):
CSV ingestion in Python, a PostgreSQL warehouse, dbt models and tests, and Power BI and
Tableau dashboards that show the same figures.

> Work in progress. The full case study (problem, architecture, model, results) comes with the
> last step of the project.

## Requirements

- Docker with Docker Compose v2
- GNU Make
- Python 3.12 and `pre-commit` for local development (optional)

## Quick start

Download the dataset from Kaggle and unzip the 9 CSV files into `data/` (they are git-ignored).
Without them, `make all DATA_DIR=data/sample` runs the whole chain on the committed sample.

```bash
git clone <this repository> && cd olist-analytics
make all        # creates .env from .env.example if needed, then up -> ingest -> build
```

| Command       | Effect                                              |
| ------------- | --------------------------------------------------- |
| `make up`     | Start the PostgreSQL 16 warehouse (`localhost:5432`) |
| `make ingest` | Load the CSV files of `DATA_DIR` (default `data/`) into the `raw` schema |
| `make build`  | Run `dbt deps` then `dbt build`                      |
| `make docs`   | Serve the dbt documentation on `localhost:8080`      |
| `make all`    | Chain `up`, `ingest` and `build`                     |
| `make down`   | Stop every service                                   |
| `make clean`  | Stop every service and delete the warehouse volume   |

Credentials live in `.env` (never committed); `.env.example` documents every variable.

## Ingestion

`ingestion/load_raw.py` loads the 9 files into the `raw` schema, one table per file. Each run
truncates and reloads every table in its own transaction, so the dbt views built on `raw` stay
valid. Values are kept as text (zip codes keep their leading zeros) and typed in dbt staging;
every row gets a `_loaded_at` timestamp for `dbt source freshness`. The script checks that all
files are present and that their headers match the expected columns before loading anything.

`data/sample/` holds about 1,000 orders with every linked customer, item, payment, review,
product and seller, for the CI. It is rebuilt deterministically from the full dataset with
`python -m ingestion.build_sample`, and it deliberately includes customers with several orders
and orders with several reviews.

## Services

| Service     | Role                                                                 |
| ----------- | -------------------------------------------------------------------- |
| `warehouse` | PostgreSQL 16, port 5432 exposed for BI tools, persistent volume     |
| `pipeline`  | Python 3.12 image with the ingestion script and dbt, started on demand |
| `docs`      | `dbt docs serve` on port 8080                                        |

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
make lint
```

pre-commit runs `sqlfluff lint` (postgres dialect), `ruff`, `ruff format`, `check-yaml` and
`end-of-file-fixer` before each commit.

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request and on every push to `main`: it starts a
PostgreSQL 16 service, runs `pre-commit`, the ingestion tests, loads `data/sample/`, then runs
`dbt deps`, `dbt build` and `dbt source freshness`. The `manifest.json`, `run_results.json` and
`sources.json` files of `dbt/target/` are published as the `dbt-target` workflow artifact.

## Data licence

The Olist dataset is published under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
