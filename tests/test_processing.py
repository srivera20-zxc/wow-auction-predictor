"""Tests for the processing layer."""

from src.processing.cleaner import clean_snapshot

SNAPSHOT = {
    "snapshot_time": "20260416T205022Z",
    "realm_id": 3676,
    "auction_count": 5,
    "auctions": [
        # Normal auction
        {"id": 1, "item": {"id": 100}, "buyout": 100_000, "quantity": 1, "time_left": "LONG"},
        # Stack of 5 — unit price should be 2g not 10g
        {"id": 2, "item": {"id": 200}, "buyout": 100_000, "quantity": 5, "time_left": "VERY_LONG"},
        # Bid-only (no buyout) — should be dropped
        {"id": 3, "item": {"id": 300}, "bid": 50_000, "quantity": 1, "time_left": "SHORT"},
        # Zero buyout — should be dropped
        {"id": 4, "item": {"id": 400}, "buyout": 0, "quantity": 1, "time_left": "LONG"},
        # Outlier (very expensive item)
        {"id": 5, "item": {"id": 500}, "buyout": 500_000_000_000, "quantity": 1, "time_left": "LONG"},
    ],
}


def test_bid_only_auctions_are_dropped():
    df = clean_snapshot(SNAPSHOT)
    assert 3 not in df["auction_id"].values


def test_zero_buyout_is_dropped():
    df = clean_snapshot(SNAPSHOT)
    assert 4 not in df["auction_id"].values


def test_copper_to_gold_conversion():
    df = clean_snapshot(SNAPSHOT)
    row = df[df["auction_id"] == 1].iloc[0]
    assert row["buyout_gold"] == 10.0  # 100_000 copper / 10_000


def test_unit_price_divides_by_quantity():
    df = clean_snapshot(SNAPSHOT)
    row = df[df["auction_id"] == 2].iloc[0]
    assert row["unit_price_gold"] == 2.0  # 10g / 5 quantity


def test_outlier_flag():
    df = clean_snapshot(SNAPSHOT)
    assert df[df["auction_id"] == 5].iloc[0]["is_outlier"] is True
    assert df[df["auction_id"] == 1].iloc[0]["is_outlier"] is False


def test_snapshot_time_parsed():
    df = clean_snapshot(SNAPSHOT)
    assert df["snapshot_time"].iloc[0].year == 2026


def test_output_columns():
    df = clean_snapshot(SNAPSHOT)
    expected = {"auction_id", "item_id", "buyout_gold", "unit_price_gold",
                "quantity", "time_left", "snapshot_time", "is_outlier"}
    assert expected.issubset(set(df.columns))
