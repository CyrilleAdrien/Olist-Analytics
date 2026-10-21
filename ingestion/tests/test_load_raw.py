import csv
import os
import uuid
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine

from ingestion import load_raw
from ingestion.load_raw import SOURCES, IngestionError

SOURCES_BY_TABLE = {source.table: source for source in SOURCES}


def write_csv(path: Path, columns: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def write_dataset(data_dir: Path) -> None:
    """Write the 9 files with headers only, then a few meaningful rows."""
    for source in SOURCES:
        write_csv(data_dir / source.file_name, source.columns, [])
    write_csv(
        data_dir / "olist_customers_dataset.csv",
        SOURCES_BY_TABLE["customers"].columns,
        [("c1", "u1", "01037", "sao paulo", "SP"), ("c2", "u1", "04571", "sao paulo", "SP")],
    )
    write_csv(
        data_dir / "olist_order_reviews_dataset.csv",
        SOURCES_BY_TABLE["order_reviews"].columns,
        [
            (
                "r1",
                "o1",
                "5",
                "",
                'Produto "ótimo",\nentrega rápida',
                "2018-01-18 00:00:00",
                "2018-01-18 21:46:59",
            )
        ],
    )


def test_every_source_maps_to_a_distinct_table():
    assert len(SOURCES) == 9
    assert len({source.table for source in SOURCES}) == 9
    assert len({source.file_name for source in SOURCES}) == 9


def test_find_missing_files_lists_absent_files(tmp_path):
    write_dataset(tmp_path)
    (tmp_path / "olist_orders_dataset.csv").unlink()

    assert load_raw.find_missing_files(tmp_path) == ["olist_orders_dataset.csv"]


def test_read_source_keeps_text_and_leading_zeros(tmp_path):
    write_dataset(tmp_path)
    source = SOURCES_BY_TABLE["customers"]

    frame = load_raw.read_source(tmp_path / source.file_name, source.columns)

    assert frame["customer_zip_code_prefix"].tolist() == ["01037", "04571"]
    assert all(pd.api.types.is_object_dtype(dtype) for dtype in frame.dtypes)


def test_read_source_turns_empty_fields_into_nulls_and_keeps_multiline_text(tmp_path):
    write_dataset(tmp_path)
    source = SOURCES_BY_TABLE["order_reviews"]

    frame = load_raw.read_source(tmp_path / source.file_name, source.columns)

    assert len(frame) == 1
    assert pd.isna(frame.loc[0, "review_comment_title"])
    assert frame.loc[0, "review_comment_message"] == 'Produto "ótimo",\nentrega rápida'


def test_read_source_strips_a_utf8_bom(tmp_path):
    source = SOURCES_BY_TABLE["product_category_name_translation"]
    path = tmp_path / source.file_name
    path.write_text(
        "product_category_name,product_category_name_english\nbeleza_saude,health_beauty\n",
        encoding="utf-8-sig",
    )

    frame = load_raw.read_source(path, source.columns)

    assert tuple(frame.columns) == source.columns


def test_read_source_rejects_unexpected_columns(tmp_path):
    source = SOURCES_BY_TABLE["sellers"]
    path = tmp_path / source.file_name
    write_csv(path, ("seller_id", "seller_city"), [("s1", "curitiba")])

    with pytest.raises(IngestionError, match="unexpected columns"):
        load_raw.read_source(path, source.columns)


def test_to_csv_buffer_writes_nulls_as_unquoted_empty_fields(tmp_path):
    write_dataset(tmp_path)
    source = SOURCES_BY_TABLE["order_reviews"]
    frame = load_raw.read_source(tmp_path / source.file_name, source.columns)

    content = load_raw.to_csv_buffer(frame).getvalue()

    assert content.startswith("r1,o1,5,,")


def test_run_fails_before_touching_the_database_when_files_are_missing(tmp_path):
    with pytest.raises(IngestionError, match="missing files"):
        load_raw.run(tmp_path, "raw", engine=None)


def test_main_returns_an_error_code_when_files_are_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "password")
    monkeypatch.setenv("POSTGRES_DB", "db")

    assert load_raw.main(["--data-dir", str(tmp_path)]) == 1


requires_database = pytest.mark.skipif(
    "POSTGRES_HOST" not in os.environ, reason="needs a PostgreSQL warehouse (POSTGRES_HOST)"
)


@requires_database
def test_run_loads_every_table_and_replaces_previous_rows(tmp_path):
    write_dataset(tmp_path)
    schema = f"test_raw_{uuid.uuid4().hex[:8]}"
    engine = create_engine(load_raw.database_url())
    try:
        load_raw.run(tmp_path, schema, engine)
        row_counts = load_raw.run(tmp_path, schema, engine)

        with engine.connect() as connection:
            customers = connection.exec_driver_sql(
                f"select customer_zip_code_prefix, _loaded_at from {schema}.customers "
                "order by customer_id"
            ).all()
            title = connection.exec_driver_sql(
                f"select review_comment_title from {schema}.order_reviews"
            ).scalar_one()

        assert row_counts["customers"] == 2
        assert row_counts["orders"] == 0
        assert [row.customer_zip_code_prefix for row in customers] == ["01037", "04571"]
        assert all(row._loaded_at is not None for row in customers)
        assert title is None
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"drop schema if exists {schema} cascade")
        engine.dispose()
