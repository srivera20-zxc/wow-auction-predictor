"""
Airflow DAG: ingest_auctions
Runs hourly. Pulls a snapshot from the Blizzard AH API, cleans it, and writes to PostgreSQL.

Task flow:
    pull_snapshot >> clean_and_store >> validate
"""

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "sebastian",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


# ---------------------------------------------------------------------------
# Task functions
# ---------------------------------------------------------------------------

def pull_snapshot(**context) -> str:
    """
    Task 1: Authenticate with Blizzard API and save a raw snapshot to disk.
    Pushes the saved file path to XCom so the next task can find it.
    """
    import os
    from src.ingestion.blizzard_client import BlizzardClient
    from src.ingestion.snapshot_store import SnapshotStore

    realm_id = int(os.environ["BLIZZARD_REALM_ID"])
    client = BlizzardClient(
        client_id=os.environ["BLIZZARD_CLIENT_ID"],
        client_secret=os.environ["BLIZZARD_CLIENT_SECRET"],
    )
    store = SnapshotStore()

    auctions = client.get_auctions(realm_id)
    path = store.save(realm_id, auctions)

    log.info("Snapshot saved: %s (%d auctions)", path, len(auctions))
    return str(path)  # XCom: returned value is automatically pushed


def clean_and_store(**context) -> int:
    """
    Task 2: Load the raw snapshot, clean it, write to PostgreSQL.
    Returns the snapshot_id for the validate task.
    """
    from src.ingestion.snapshot_store import SnapshotStore
    from src.processing.cleaner import clean_snapshot
    from src.utils.db import create_tables, write_clean_snapshot
    import os

    # Pull the file path written by task 1 via XCom
    ti = context["ti"]
    raw_path = ti.xcom_pull(task_ids="pull_snapshot")

    store = SnapshotStore()
    raw = store.load(raw_path)

    df = clean_snapshot(raw)
    log.info("Cleaned snapshot: %d rows", len(df))

    create_tables()  # no-op if tables already exist

    realm_id = int(os.environ["BLIZZARD_REALM_ID"])
    snapshot_id = write_clean_snapshot(
        df=df,
        realm_id=realm_id,
        snapshot_time=df["snapshot_time"].iloc[0],
    )
    log.info("Wrote snapshot_id=%d to database", snapshot_id)
    return snapshot_id


def validate(**context) -> None:
    """
    Task 3: Basic data quality checks. Fails the task (raises) if something looks wrong.
    This prevents silently collecting garbage data.
    """
    from src.utils.db import get_engine
    from sqlalchemy import text

    ti = context["ti"]
    snapshot_id = ti.xcom_pull(task_ids="clean_and_store")

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM auctions WHERE snapshot_id = :sid"),
            {"sid": snapshot_id},
        )
        row_count = result.scalar()

    log.info("Validation: snapshot_id=%d has %d rows", snapshot_id, row_count)

    if row_count < 1000:
        raise ValueError(
            f"Snapshot {snapshot_id} has only {row_count} rows — "
            "expected at least 1000. Possible API issue."
        )

    log.info("Validation passed.")


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

with DAG(
    dag_id="ingest_auctions",
    description="Hourly: pull AH snapshot → clean → store in PostgreSQL",
    schedule_interval="@hourly",
    start_date=datetime(2026, 4, 16),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["ingestion", "blizzard"],
) as dag:

    t1 = PythonOperator(
        task_id="pull_snapshot",
        python_callable=pull_snapshot,
    )

    t2 = PythonOperator(
        task_id="clean_and_store",
        python_callable=clean_and_store,
    )

    t3 = PythonOperator(
        task_id="validate",
        python_callable=validate,
    )

    # Wire the pipeline: pull → clean → validate
    t1 >> t2 >> t3
