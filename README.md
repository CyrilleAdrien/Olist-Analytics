# Olist Analytics

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

```bash
git clone <this repository> && cd olist-analytics
make all        # creates .env from .env.example if needed, then up -> ingest -> build
```

| Command       | Effect                                              |
| ------------- | --------------------------------------------------- |
| `make up`     | Start the PostgreSQL 16 warehouse (`localhost:5432`) |
| `make ingest` | Load the Olist CSV files into the `raw` schema       |
| `make build`  | Run `dbt deps` then `dbt build`                      |
| `make docs`   | Serve the dbt documentation on `localhost:8080`      |
| `make all`    | Chain `up`, `ingest` and `build`                     |
| `make down`   | Stop every service                                   |
| `make clean`  | Stop every service and delete the warehouse volume   |

Credentials live in `.env` (never committed); `.env.example` documents every variable.

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

## Data licence

The Olist dataset is published under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
