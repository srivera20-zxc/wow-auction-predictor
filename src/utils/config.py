"""Application settings loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    blizzard_client_id: str
    blizzard_client_secret: str
    blizzard_realm_id: int
    database_url: str
    mlflow_tracking_uri: str
    app_env: str


def get_settings() -> Settings:
    """Load and validate settings from environment."""
    client_id = os.environ.get("BLIZZARD_CLIENT_ID", "")
    client_secret = os.environ.get("BLIZZARD_CLIENT_SECRET", "")
    realm_id = os.environ.get("BLIZZARD_REALM_ID", "0")

    if not client_id or not client_secret:
        raise ValueError("BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET must be set")

    return Settings(
        blizzard_client_id=client_id,
        blizzard_client_secret=client_secret,
        blizzard_realm_id=int(realm_id),
        database_url=os.environ.get("DATABASE_URL", ""),
        mlflow_tracking_uri=os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"),
        app_env=os.environ.get("APP_ENV", "development"),
    )
