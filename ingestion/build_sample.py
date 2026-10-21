"""Build the CI sample in data/sample/ from the full Olist dataset in data/.

The sample keeps about 1,000 orders with every linked row in the other files, so that the
dbt relationships tests hold. It deliberately includes the two data pitfalls the models must
handle: customers who ordered more than once (same customer_unique_id, several customer_id)
and orders with more than one review. Geolocation keeps one row per zip code prefix in use,
which keeps the file small; no model relies on the other rows.

Usage:
    python -m ingestion.build_sample [--source-dir data] [--target-dir data/sample]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from ingestion.load_raw import SOURCES, IngestionError, find_missing_files, read_source

SEED = 42
RANDOM_ORDERS = 950
REPEAT_CUSTOMERS = 20
MULTI_REVIEW_ORDERS = 20


def read_all(source_dir: Path) -> dict[str, pd.DataFrame]:
    missing = find_missing_files(source_dir)
    if missing:
        raise IngestionError(f"missing files in {source_dir}: {', '.join(missing)}")
    return {
        source.table: read_source(source_dir / source.file_name, source.columns)
        for source in SOURCES
    }


def pick_order_ids(tables: dict[str, pd.DataFrame]) -> set[str]:
    orders = tables["orders"].merge(
        tables["customers"][["customer_id", "customer_unique_id"]], on="customer_id"
    )

    orders_per_customer = orders.groupby("customer_unique_id")["order_id"].nunique()
    repeat_customers = orders_per_customer[orders_per_customer > 1].index.to_series()
    picked_customers = repeat_customers.sample(
        min(REPEAT_CUSTOMERS, len(repeat_customers)), random_state=SEED
    )
    repeat_orders = orders.loc[orders["customer_unique_id"].isin(picked_customers), "order_id"]

    reviews_per_order = tables["order_reviews"].groupby("order_id")["review_id"].count()
    multi_review = reviews_per_order[reviews_per_order > 1].index.to_series()
    multi_review_orders = multi_review.sample(
        min(MULTI_REVIEW_ORDERS, len(multi_review)), random_state=SEED
    )

    random_orders = orders["order_id"].sample(min(RANDOM_ORDERS, len(orders)), random_state=SEED)
    return set(random_orders) | set(repeat_orders) | set(multi_review_orders)


def build_sample(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    order_ids = pick_order_ids(tables)

    orders = tables["orders"][tables["orders"]["order_id"].isin(order_ids)]
    order_items = tables["order_items"][tables["order_items"]["order_id"].isin(order_ids)]
    order_payments = tables["order_payments"][tables["order_payments"]["order_id"].isin(order_ids)]
    order_reviews = tables["order_reviews"][tables["order_reviews"]["order_id"].isin(order_ids)]
    customers = tables["customers"][tables["customers"]["customer_id"].isin(orders["customer_id"])]
    products = tables["products"][tables["products"]["product_id"].isin(order_items["product_id"])]
    sellers = tables["sellers"][tables["sellers"]["seller_id"].isin(order_items["seller_id"])]

    zip_prefixes = set(customers["customer_zip_code_prefix"]) | set(
        sellers["seller_zip_code_prefix"]
    )
    geolocation = tables["geolocation"][
        tables["geolocation"]["geolocation_zip_code_prefix"].isin(zip_prefixes)
    ].drop_duplicates("geolocation_zip_code_prefix")

    return {
        "customers": customers,
        "geolocation": geolocation,
        "order_items": order_items,
        "order_payments": order_payments,
        "order_reviews": order_reviews,
        "orders": orders,
        "products": products,
        "sellers": sellers,
        # Small reference table, kept whole
        "product_category_name_translation": tables["product_category_name_translation"],
    }


def write_sample(sample: dict[str, pd.DataFrame], target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for source in SOURCES:
        sample[source.table].to_csv(target_dir / source.file_name, index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source-dir", type=Path, default=Path("data"))
    parser.add_argument("--target-dir", type=Path, default=Path("data/sample"))
    args = parser.parse_args(argv)

    try:
        sample = build_sample(read_all(args.source_dir))
    except IngestionError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    write_sample(sample, args.target_dir)
    for table, frame in sample.items():
        print(f"{table}: {len(frame)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
