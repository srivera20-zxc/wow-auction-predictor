"""Database connection and ORM models."""

import os
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class Snapshot(Base):
    """One hourly pull from the Blizzard AH API."""

    __tablename__ = "snapshots"
    __table_args__ = (UniqueConstraint("realm_id", "snapshot_time"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    realm_id = Column(Integer, nullable=False)
    snapshot_time = Column(DateTime(timezone=True), nullable=False)
    auction_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Auction(Base):
    """A single auction listing from a snapshot."""

    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    auction_id = Column(BigInteger, nullable=False)
    item_id = Column(Integer, nullable=False, index=True)
    buyout_gold = Column(Numeric(14, 4))
    unit_price_gold = Column(Numeric(14, 4))
    quantity = Column(Integer, nullable=False)
    time_left = Column(String(20))
    snapshot_time = Column(DateTime(timezone=True), nullable=False, index=True)
    is_outlier = Column(Boolean, default=False)


def get_engine():
    """Create SQLAlchemy engine from DATABASE_URL env var."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return create_engine(url, pool_pre_ping=True)


def get_session_factory():
    return sessionmaker(bind=get_engine())


def create_tables() -> None:
    """Create all tables if they don't exist (idempotent)."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def write_clean_snapshot(df, realm_id: int, snapshot_time: datetime) -> int:
    """
    Insert a cleaned snapshot DataFrame into the database.

    Returns the snapshot_id of the inserted snapshot row.
    Skips the snapshot entirely if it already exists (idempotent).
    """
    engine = get_engine()
    SessionFactory = sessionmaker(bind=engine)

    with SessionFactory() as session:
        # Check if this snapshot already exists
        existing = (
            session.query(Snapshot)
            .filter_by(realm_id=realm_id, snapshot_time=snapshot_time)
            .first()
        )
        if existing:
            return existing.id

        # Insert snapshot header
        snapshot = Snapshot(
            realm_id=realm_id,
            snapshot_time=snapshot_time,
            auction_count=len(df),
        )
        session.add(snapshot)
        session.flush()  # get snapshot.id before bulk insert

        # Bulk insert auction rows
        rows = [
            {
                "snapshot_id": snapshot.id,
                "auction_id": row.auction_id,
                "item_id": row.item_id,
                "buyout_gold": row.buyout_gold,
                "unit_price_gold": row.unit_price_gold,
                "quantity": row.quantity,
                "time_left": row.time_left,
                "snapshot_time": row.snapshot_time,
                "is_outlier": row.is_outlier,
            }
            for row in df.itertuples(index=False)
        ]
        session.bulk_insert_mappings(Auction, rows)
        session.commit()

        return snapshot.id
