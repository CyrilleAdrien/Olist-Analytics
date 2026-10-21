import pandas as pd

from ingestion import build_sample
from ingestion.load_raw import SOURCES


def frame(table: str, rows: list[tuple[str, ...]]) -> pd.DataFrame:
    columns = next(source.columns for source in SOURCES if source.table == table)
    return pd.DataFrame(rows, columns=list(columns), dtype=object)


def full_dataset() -> dict[str, pd.DataFrame]:
    """Two customers share a customer_unique_id; order o2 has two reviews."""
    return {
        "customers": frame(
            "customers",
            [
                ("c1", "u1", "01037", "sao paulo", "SP"),
                ("c2", "u1", "01037", "sao paulo", "SP"),
                ("c3", "u3", "80000", "curitiba", "PR"),
                ("c9", "u9", "99999", "unused", "RS"),
            ],
        ),
        "orders": frame(
            "orders",
            [
                (f"o{i}", f"c{i}", "delivered", "2018-01-01 10:00:00", "", "", "", "")
                for i in (1, 2, 3)
            ],
        ),
        "order_items": frame(
            "order_items",
            [("o1", "1", "p1", "s1", "", "10.00", "1.50"), ("o3", "1", "p2", "s1", "", "5.0", "1")],
        ),
        "order_payments": frame("order_payments", [("o1", "1", "boleto", "1", "11.50")]),
        "order_reviews": frame(
            "order_reviews",
            [
                ("r1", "o2", "1", "", "", "2018-01-02 00:00:00", ""),
                ("r2", "o2", "4", "", "", "2018-01-05 00:00:00", ""),
            ],
        ),
        "products": frame(
            "products",
            [
                ("p1", "beleza_saude", "", "", "", "", "", "", ""),
                ("p8", "x", "", "", "", "", "", "", ""),
            ],
        ),
        "sellers": frame("sellers", [("s1", "80000", "curitiba", "PR")]),
        "geolocation": frame(
            "geolocation",
            [
                ("01037", "-23.54", "-46.63", "sao paulo", "SP"),
                ("01037", "-23.55", "-46.64", "sao paulo", "SP"),
                ("80000", "-25.42", "-49.27", "curitiba", "PR"),
                ("99999", "0", "0", "unused", "RS"),
            ],
        ),
        "product_category_name_translation": frame(
            "product_category_name_translation", [("beleza_saude", "health_beauty")]
        ),
    }


def test_sample_keeps_every_linked_row_and_nothing_else():
    sample = build_sample.build_sample(full_dataset())

    assert set(sample["orders"]["order_id"]) == {"o1", "o2", "o3"}
    assert set(sample["customers"]["customer_id"]) == {"c1", "c2", "c3"}
    assert set(sample["products"]["product_id"]) == {"p1"}
    assert set(sample["sellers"]["seller_id"]) == {"s1"}
    assert len(sample["order_reviews"]) == 2


def test_sample_keeps_one_geolocation_row_per_zip_prefix_in_use():
    sample = build_sample.build_sample(full_dataset())

    assert sample["geolocation"]["geolocation_zip_code_prefix"].tolist() == ["01037", "80000"]


def test_pick_order_ids_includes_repeat_customers_and_multi_review_orders(monkeypatch):
    monkeypatch.setattr(build_sample, "RANDOM_ORDERS", 0)

    order_ids = build_sample.pick_order_ids(full_dataset())

    # o1 and o2 belong to the repeat customer u1, o2 also has two reviews
    assert order_ids == {"o1", "o2"}


def test_write_sample_round_trips_through_read_source(tmp_path):
    sample = build_sample.build_sample(full_dataset())

    build_sample.write_sample(sample, tmp_path)
    reread = build_sample.read_all(tmp_path)

    assert reread["customers"]["customer_zip_code_prefix"].tolist() == ["01037", "01037", "80000"]
    assert len(reread["orders"]) == 3
