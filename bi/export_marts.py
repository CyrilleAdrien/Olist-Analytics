"""Export the marts tables to CSV in bi/exports/, for Tableau Public.

Tableau Public cannot connect to PostgreSQL, so it reads these files instead. They are a
snapshot of the warehouse: run `make export` again after each `make build`.

Usage:
    python bi/export_marts.py [--target-dir bi/exports]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.load_raw import database_url  # noqa: E402

TABLES = (
    "fct_orders",
    "fct_order_items",
    "dim_customers",
    "dim_products",
    "dim_sellers",
    "dim_dates",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target-dir", type=Path, default=Path("bi/exports"))
    parser.add_argument("--schema", default="marts")
    args = parser.parse_args(argv)

    args.target_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url())
    try:
        with engine.connect() as connection:
            for table in TABLES:
                frame = pd.read_sql_table(
                    table, connection, schema=args.schema, dtype_backend="numpy_nullable"
                )
                frame.to_csv(args.target_dir / f"{table}.csv", index=False)
                print(f"{table}: {len(frame)} rows")
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
