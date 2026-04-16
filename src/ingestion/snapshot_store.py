"""Persist raw auction snapshots to disk as gzipped JSON."""

import gzip
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


class SnapshotStore:
    """Writes raw API responses to data/raw/<realm_id>/<timestamp>.json.gz"""

    def __init__(self, base_dir: Path = RAW_DIR) -> None:
        self.base_dir = base_dir

    def save(self, realm_id: int, auctions: list[dict[str, Any]]) -> Path:
        """Persist a snapshot and return the file path written."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        realm_dir = self.base_dir / str(realm_id)
        realm_dir.mkdir(parents=True, exist_ok=True)

        path = realm_dir / f"{ts}.json.gz"
        payload = {
            "snapshot_time": ts,
            "realm_id": realm_id,
            "auction_count": len(auctions),
            "auctions": auctions,
        }
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(payload, f)

        logger.info("Saved snapshot: %s (%d auctions)", path, len(auctions))
        return path

    def load(self, path: Path) -> dict[str, Any]:
        """Load a previously saved snapshot."""
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    def list_snapshots(self, realm_id: int) -> list[Path]:
        """Return sorted list of snapshot paths for a realm."""
        realm_dir = self.base_dir / str(realm_id)
        if not realm_dir.exists():
            return []
        return sorted(realm_dir.glob("*.json.gz"))
