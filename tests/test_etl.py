"""Tests for the transform step of etl_pipeline.py."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from etl_pipeline import parse_date, transform  # noqa: E402


def _raw(rows):
    cols = ["order_id", "order_date", "product_name", "quantity", "unit_price",
            "currency", "region", "sales_rep"]
    return pd.DataFrame(rows, columns=cols)


def test_parse_date_formats():
    assert parse_date("03/15/2024") == "2024-03-15"
    assert parse_date("2024-03-15") == "2024-03-15"
    assert parse_date("15-Mar-2024") == "2024-03-15"
    assert parse_date("not a date") is None


def test_transform_cleans_and_converts():
    df = transform(_raw([
        ["SO-1", "03/15/2024", " Laptop Pro 14 ", 2, "$100.00", "USD", "North America", "bob_smith"],
        ["SO-1", "03/15/2024", "Laptop Pro 14", 2, "$100.00", "USD", "North America", "bob_smith"],  # dup
        ["SO-2", "", "Docking Station", 1, 50, "EUR", "Europe", "emma_brown"],                       # no date
        ["SO-3", "2024-04-01", "Firewall Appliance", -3, 10, "USD", "Asia Pacific", "david_lee"],    # cancel
        ["SO-4", "01-Feb-2024", "CRM License (annual)", 1, 200, "GBP", "UK & Ireland", "grace_chen"],
    ]))
    assert list(df.order_id) == ["SO-1", "SO-4"]
    first, gbp = df.iloc[0], df.iloc[1]
    assert first.product_name == "Laptop Pro 14"
    assert first.order_date == "2024-03-15" and first.order_month == "2024-03"
    assert first.revenue_usd == 200.0
    assert first.sales_rep == "Bob Smith"
    assert gbp.order_date == "2024-02-01"
    assert gbp.revenue_usd == 254.0                     # 200 GBP x 1.27
