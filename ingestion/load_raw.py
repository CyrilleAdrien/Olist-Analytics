"""Load the Olist CSV files into the `raw` schema of the PostgreSQL warehouse.

Every table is fully replaced on each run, in its own transaction. Values are loaded as text:
typing happens in the dbt staging layer, which keeps leading zeros in zip codes and never
guesses a format here.
Each table gets a `_loaded_at` column, used by dbt source freshness.

Usage:
    python ingestion/load_raw.py [--data-dir data] [--schema raw]
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL

LOGGER = logging.getLogger("load_raw")

LOADED_AT_COLUMN = "_loaded_at"


@dataclass(frozen=True)
class SourceFile:
    file_name: str
    table: str
    columns: tuple[str, ...]


SOURCES: tuple[SourceFile, ...] = (
    SourceFile(
        "olist_customers_dataset.csv",
        "customers",
        (
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
    ),
    SourceFile(
        "olist_geolocation_dataset.csv",
        "geolocation",
        (
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ),
    ),
    SourceFile(
        "olist_order_items_dataset.csv",
        "order_items",
        (
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ),
    ),
    SourceFile(
        "olist_order_payments_dataset.csv",
        "order_payments",
        (
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ),
    ),
    SourceFile(
        "olist_order_reviews_dataset.csv",
        "order_reviews",
        (
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ),
    ),
    SourceFile(
        "olist_orders_dataset.csv",
        "orders",
        (
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
    ),
    SourceFile(
        "olist_products_dataset.csv",
        "products",
        (
            "product_id",
            "product_category_name",
            # The misspelling "lenght" comes from the source file and is fixed in staging
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
    ),
    SourceFile(
        "olist_sellers_dataset.csv",
        "sellers",
        ("seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"),
    ),
    SourceFile(
        "product_category_name_translation.csv",
        "product_category_name_translation",
        ("product_category_name", "product_category_name_english"),
    ),
)


class IngestionError(Exception):
    """Raised when the input files do not match the expected Olist layout."""


def find_missing_files(data_dir: Path) -> list[str]:
    return [source.file_name for source in SOURCES if not (data_dir / source.file_name).is_file()]


def read_source(path: Path, expected_columns: tuple[str, ...]) -> pd.DataFrame:
    """Read a CSV as text, with empty fields as nulls, and check its header."""
    frame = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
        encoding="utf-8-sig",
    )
    if tuple(frame.columns) != expected_columns:
        raise IngestionError(
            f"{path.name}: unexpected columns {list(frame.columns)}, "
            f"expected {list(expected_columns)}"
        )
    return frame


def to_csv_buffer(frame: pd.DataFrame) -> io.StringIO:
    """Serialise a frame for COPY ... FROM STDIN (CSV), nulls as unquoted empty fields."""
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    return buffer


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def load_table(
    engine: Engine,
    schema: str,
    source: SourceFile,
    frame: pd.DataFrame,
    loaded_at: datetime,
) -> None:
    table = f"{quote_identifier(schema)}.{quote_identifier(source.table)}"
    column_definitions = ", ".join(f"{quote_identifier(column)} text" for column in source.columns)
    column_list = ", ".join(
        quote_identifier(column) for column in (*source.columns, LOADED_AT_COLUMN)
    )

    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            # Truncate instead of drop: the dbt staging views built on raw tables stay valid
            cursor.execute(
                f"create table if not exists {table} ({column_definitions}, "
                f"{quote_identifier(LOADED_AT_COLUMN)} timestamptz not null)"
            )
            cursor.execute(f"truncate table {table}")
            buffer = to_csv_buffer(frame.assign(**{LOADED_AT_COLUMN: loaded_at.isoformat()}))
            with cursor.copy(f"copy {table} ({column_list}) from stdin with (format csv)") as copy:
                while chunk := buffer.read(1 << 20):
                    copy.write(chunk)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def database_url() -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )


def run(data_dir: Path, schema: str, engine: Engine) -> dict[str, int]:
    """Load every source file and return the number of rows loaded per table."""
    missing = find_missing_files(data_dir)
    if missing:
        raise IngestionError(f"missing files in {data_dir}: {', '.join(missing)}")

    with engine.begin() as connection:
        connection.exec_driver_sql(f"create schema if not exists {quote_identifier(schema)}")

    loaded_at = datetime.now(UTC)
    row_counts: dict[str, int] = {}
    for source in SOURCES:
        frame = read_source(data_dir / source.file_name, source.columns)
        load_table(engine, schema, source, frame, loaded_at)
        row_counts[source.table] = len(frame)
        LOGGER.info("%s.%s: %d rows", schema, source.table, len(frame))
    return row_counts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("DATA_DIR", "data")),
        help="folder that contains the 9 Olist CSV files (default: data)",
    )
    parser.add_argument("--schema", default="raw", help="target schema (default: raw)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args(argv)
    engine = create_engine(database_url())
    try:
        row_counts = run(args.data_dir, args.schema, engine)
    except IngestionError as error:
        LOGGER.error("%s", error)
        return 1
    finally:
        engine.dispose()
    LOGGER.info("Loaded %d tables, %d rows", len(row_counts), sum(row_counts.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
