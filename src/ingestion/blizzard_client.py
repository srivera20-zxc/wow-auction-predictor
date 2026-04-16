"""Blizzard Battle.net API client with OAuth2 and Auction House endpoints."""

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth.battle.net/token"
API_BASE = "https://us.api.blizzard.com"
NAMESPACE = "dynamic-us"
LOCALE = "en_US"


class BlizzardClient:
    """Thin wrapper around the Blizzard Battle.net API."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _refresh_token(self) -> None:
        """Fetch a new OAuth2 client-credentials token."""
        response = self._session.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        self._access_token = data["access_token"]
        # Expire slightly early to avoid edge-case races
        self._token_expires_at = time.time() + data["expires_in"] - 60
        logger.debug("Blizzard OAuth token refreshed")

    def _get_headers(self) -> dict[str, str]:
        if time.time() >= self._token_expires_at:
            self._refresh_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    # ------------------------------------------------------------------
    # Auction House
    # ------------------------------------------------------------------

    def get_auctions(self, connected_realm_id: int) -> list[dict[str, Any]]:
        """
        Fetch current auction listings for a connected realm.

        Returns a list of raw auction dicts as returned by the Blizzard API.
        Prices are in copper (divide by 10_000 for gold).
        """
        url = f"{API_BASE}/data/wow/connected-realm/{connected_realm_id}/auctions"
        params = {"namespace": NAMESPACE, "locale": LOCALE}

        response = self._session.get(
            url, headers=self._get_headers(), params=params, timeout=30
        )
        response.raise_for_status()
        data = response.json()
        auctions: list[dict[str, Any]] = data.get("auctions", [])
        logger.info(
            "Fetched %d auctions for realm %d", len(auctions), connected_realm_id
        )
        return auctions

    # ------------------------------------------------------------------
    # Item metadata
    # ------------------------------------------------------------------

    def get_item(self, item_id: int) -> dict[str, Any]:
        """Fetch item metadata (name, quality, item class, etc.)."""
        url = f"{API_BASE}/data/wow/item/{item_id}"
        params = {"namespace": "static-us", "locale": LOCALE}

        response = self._session.get(
            url, headers=self._get_headers(), params=params, timeout=10
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def get_connected_realms(self) -> list[dict[str, Any]]:
        """List all connected realm IDs (useful for finding your realm ID)."""
        url = f"{API_BASE}/data/wow/connected-realm/index"
        params = {"namespace": NAMESPACE, "locale": LOCALE}

        response = self._session.get(
            url, headers=self._get_headers(), params=params, timeout=10
        )
        response.raise_for_status()
        return response.json().get("connected_realms", [])  # type: ignore[no-any-return]
