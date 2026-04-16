"""Tests for ingestion layer."""

import gzip
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.blizzard_client import BlizzardClient
from src.ingestion.snapshot_store import SnapshotStore


# ---------------------------------------------------------------------------
# BlizzardClient
# ---------------------------------------------------------------------------

FAKE_TOKEN_RESPONSE = {"access_token": "test-token-abc", "expires_in": 86400}

FAKE_AUCTIONS = [
    {"id": 1, "item": {"id": 6513}, "buyout": 100000, "quantity": 1, "time_left": "LONG"},
    {"id": 2, "item": {"id": 858}, "buyout": 50000, "quantity": 5, "time_left": "VERY_LONG"},
]


def _mock_session(token_response: dict, api_response: dict) -> MagicMock:
    session = MagicMock()
    token_resp = MagicMock()
    token_resp.json.return_value = token_response
    token_resp.raise_for_status = MagicMock()

    api_resp = MagicMock()
    api_resp.json.return_value = api_response
    api_resp.raise_for_status = MagicMock()

    session.post.return_value = token_resp
    session.get.return_value = api_resp
    return session


def test_get_auctions_returns_list():
    client = BlizzardClient("fake-id", "fake-secret")
    client._session = _mock_session(
        FAKE_TOKEN_RESPONSE, {"auctions": FAKE_AUCTIONS}
    )

    result = client.get_auctions(connected_realm_id=1370)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["id"] == 1


def test_token_is_reused_within_expiry():
    client = BlizzardClient("fake-id", "fake-secret")
    client._session = _mock_session(
        FAKE_TOKEN_RESPONSE, {"auctions": FAKE_AUCTIONS}
    )

    client.get_auctions(1370)
    client.get_auctions(1370)

    # Token endpoint should only be called once
    assert client._session.post.call_count == 1


# ---------------------------------------------------------------------------
# SnapshotStore
# ---------------------------------------------------------------------------

def test_save_and_load_snapshot(tmp_path: Path):
    store = SnapshotStore(base_dir=tmp_path)
    auctions = [{"id": 99, "buyout": 200000}]

    saved_path = store.save(realm_id=1370, auctions=auctions)

    assert saved_path.exists()
    loaded = store.load(saved_path)
    assert loaded["realm_id"] == 1370
    assert loaded["auction_count"] == 1
    assert loaded["auctions"][0]["id"] == 99


def test_list_snapshots_sorted(tmp_path: Path):
    store = SnapshotStore(base_dir=tmp_path)

    store.save(realm_id=1370, auctions=[{"id": 1}])
    store.save(realm_id=1370, auctions=[{"id": 2}])

    snapshots = store.list_snapshots(realm_id=1370)
    assert len(snapshots) == 2
    # Should be sorted chronologically
    assert snapshots[0] < snapshots[1]


def test_list_snapshots_empty_for_unknown_realm(tmp_path: Path):
    store = SnapshotStore(base_dir=tmp_path)
    assert store.list_snapshots(realm_id=9999) == []
