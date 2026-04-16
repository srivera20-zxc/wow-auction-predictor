"""Clean and normalize raw auction snapshots."""

import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)

COPPER_PER_GOLD = 10_000

# Auctions above this unit price are almost certainly TCG items / outliers.
# We keep them in the DB but flag them so the model can exclude them.
OUTLIER_THRESHOLD_GOLD = 5_000_000


def clean_snapshot(raw: dict) -> pd.DataFrame:
    """
    Convert a raw snapshot dict (as loaded by SnapshotStore) into a clean DataFrame.

    Each row is one auction listing with normalized prices and basic quality flags.

    Columns returned:
        auction_id, item_id, buyout_gold, unit_price_gold, quantity,
        time_left, snapshot_time, is_outlier
    """
    auctions = raw.get("auctions", [])
    snapshot_time = _parse_snapshot_time(raw.get("snapshot_time", ""))

    rows = []
    for a in auctions:
        buyout_copper = a.get("buyout")

        # Skip bid-only auctions — no buyout means no price signal for prediction
        if buyout_copper is None:
            continue

        quantity = a.get("quantity", 1)

        # Skip malformed rows
        if quantity <= 0 or buyout_copper <= 0:
            continue

        buyout_gold = buyout_copper / COPPER_PER_GOLD
        unit_price_gold = buyout_gold / quantity

        rows.append({
            "auction_id": a["id"],
            "item_id": a["item"]["id"],
            "buyout_gold": round(buyout_gold, 4),
            "unit_price_gold": round(unit_price_gold, 4),
            "quantity": quantity,
            "time_left": a.get("time_left", "UNKNOWN"),
            "snapshot_time": snapshot_time,
            "is_outlier": unit_price_gold > OUTLIER_THRESHOLD_GOLD,
        })

    df = pd.DataFrame(rows)

    if df.empty:
        logger.warning("Cleaner produced empty DataFrame for snapshot %s", snapshot_time)
        return df

    dropped = len(auctions) - len(df)
    logger.info(
        "Cleaned snapshot %s: %d → %d rows (%d dropped)",
        snapshot_time, len(auctions), len(df), dropped,
    )
    return df


def _parse_snapshot_time(ts_str: str) -> datetime:
    """Parse snapshot timestamp string (e.g. '20260416T205022Z') to datetime."""
    try:
        return datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
