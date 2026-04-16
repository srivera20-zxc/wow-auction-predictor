# WoW Auction House Price Predictor

![CI](https://github.com/srivera20-zxc/wow-auction-predictor/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-red)
![Airflow](https://img.shields.io/badge/Airflow-2.7+-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

An end-to-end ML pipeline that ingests World of Warcraft Auction House data from the Blizzard API, processes it, and trains a PyTorch model to predict optimal item sell prices and listing times.

## The Problem

> Given an item's historical auction data — price, quantity, time of day, day of week, days since last patch — predict the optimal sell price and best time to list.

This is demand forecasting + price optimization applied to a virtual economy with real market dynamics: supply/demand shocks from patch cycles, speculation, raid tier releases, and seasonal trends.

## Architecture

```
Blizzard API (hourly snapshots)
    │
    ▼
[Airflow DAG: ingest_auctions]          hourly
    ├── OAuth2 token refresh
    └── Raw JSON → data/raw/<realm>/<timestamp>.json.gz
    │
    ▼
[Airflow DAG: process_auctions]         hourly
    ├── Deduplicate, normalize copper → gold
    ├── Enrich with item metadata (name, category, quality)
    └── Write to PostgreSQL
    │
    ▼
[Airflow DAG: train_model]              daily
    ├── Feature engineering
    │   ├── Rolling price averages (1h, 6h, 24h, 7d)
    │   ├── Supply volume trends
    │   ├── Time features (hour, day_of_week, days_since_patch)
    │   └── Price volatility metrics
    ├── PyTorch model training (MLP → LSTM)
    └── Log to MLflow → register best model
    │
    ▼
[FastAPI serving endpoint]
    ├── GET /predict?item_id=X&realm=Y
    ├── GET /items/{item_id}/history
    └── GET /health
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Data source | Blizzard Battle.net API |
| Orchestration | Apache Airflow |
| ML | PyTorch (MLP → LSTM) |
| Experiment tracking | MLflow |
| Database | PostgreSQL |
| Serving | FastAPI |
| Containers | Docker + docker-compose |
| CI/CD | GitHub Actions |

## Project Structure

```
wow-auction-predictor/
├── dags/               # Airflow DAGs (ingest, process, train)
├── src/
│   ├── ingestion/      # Blizzard API client + snapshot storage
│   ├── processing/     # Cleaner, enricher, feature engineering
│   ├── models/         # PyTorch dataset, network, training loop
│   ├── serving/        # FastAPI app
│   └── utils/          # Config, DB helpers
├── notebooks/          # EDA and experiment notebooks
├── tests/              # Unit tests
└── mlflow/             # MLflow server Dockerfile
```

## Quickstart

### 1. Clone and configure

```bash
git clone https://github.com/srivera20-zxc/wow-auction-predictor.git
cd wow-auction-predictor
cp .env.example .env
# Fill in BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET, BLIZZARD_REALM_ID
```

Get API credentials at [develop.battle.net](https://develop.battle.net/).

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Run tests

```bash
pytest tests/ -v
```

### 4. Pull your first snapshot

```python
from src.utils.config import get_settings
from src.ingestion.blizzard_client import BlizzardClient
from src.ingestion.snapshot_store import SnapshotStore

settings = get_settings()
client = BlizzardClient(settings.blizzard_client_id, settings.blizzard_client_secret)
store = SnapshotStore()

auctions = client.get_auctions(settings.blizzard_realm_id)
path = store.save(settings.blizzard_realm_id, auctions)
print(f"Saved {len(auctions)} auctions to {path}")
```

### 5. Full stack (coming soon)

```bash
docker-compose up
```

## Status

| Phase | Status |
|---|---|
| Phase 1: Data Ingestion | In progress |
| Phase 2: Processing Pipeline | Not started |
| Phase 3: Model Development | Not started |
| Phase 4: Serving + Polish | Not started |

## License

MIT
