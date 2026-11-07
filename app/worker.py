"""Database-polling worker with lease-based recovery of abandoned claims."""

import logging
import os
import signal
import threading
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

import redis
from prometheus_client import Counter, Gauge, start_http_server
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db import _session_factory, database_url
from app.models import Order

POLL_SECONDS = max(0.1, min(60.0, float(os.getenv("WORKER_POLL_SECONDS", "1"))))
PROCESS_SECONDS = max(0.0, min(60.0, float(os.getenv("WORKER_PROCESS_SECONDS", "2"))))
LEASE_SECONDS = max(300, PROCESS_SECONDS + 30)
COMPLETED = Counter(
    "releaseops_worker_orders_total", "Worker order completions", ["result"]
)
QUEUE_DEPTH = Gauge("releaseops_queued_orders", "Orders waiting for processing")
HEARTBEAT = Gauge(
    "releaseops_worker_heartbeat_timestamp_seconds",
    "Unix timestamp of the latest worker loop",
)
WORKER_ERRORS = Counter(
    "releaseops_worker_errors_total", "Unexpected worker loop errors"
)
stopping = threading.Event()
wake_event = threading.Event()
logger = logging.getLogger("releaseops.worker")


def process_one(session: Session) -> UUID | None:
    """Claim one row in a short transaction, simulate work, then finalize atomically.

    PostgreSQL uses SKIP LOCKED so several workers can claim different rows. Other
    databases use a conditional update so only one worker wins the selected row.
    """
    now = datetime.now(UTC)
    stale_before = now - timedelta(seconds=LEASE_SECONDS)
    session.execute(
        update(Order)
        .where(Order.status == "processing", Order.claimed_at < stale_before)
        .values(status="queued", claimed_at=None)
    )
    session.commit()
    query = (
        select(Order)
        .where(Order.status == "queued")
        .order_by(Order.created_at, Order.id)
        .limit(1)
    )
    if session.bind and session.bind.dialect.name == "postgresql":
        query = query.with_for_update(skip_locked=True)
    candidate = session.scalar(query)
    if candidate is None:
        session.rollback()
        return None
    order_id = candidate.id
    result = session.execute(
        update(Order)
        .where(Order.id == order_id, Order.status == "queued")
        .values(status="processing", claimed_at=now)
    )
    session.commit()
    if result.rowcount != 1:
        return None

    try:
        if PROCESS_SECONDS and stopping.wait(PROCESS_SECONDS):
            # Safe synthetic work can be immediately requeued on an orderly shutdown.
            session.execute(
                update(Order)
                .where(
                    Order.id == order_id,
                    Order.status == "processing",
                    Order.claimed_at == now,
                )
                .values(status="queued", claimed_at=None)
            )
            session.commit()
            return order_id
        result = session.execute(
            update(Order)
            .where(
                Order.id == order_id,
                Order.status == "processing",
                Order.claimed_at == now,
            )
            .values(status="completed", finished_at=datetime.now(UTC))
        )
        session.commit()
        if result.rowcount == 1:
            COMPLETED.labels("completed").inc()
        return order_id
    except Exception:
        session.rollback()
        session.execute(
            update(Order)
            .where(
                Order.id == order_id,
                Order.status == "processing",
                Order.claimed_at == now,
            )
            .values(status="failed", finished_at=datetime.now(UTC))
        )
        session.commit()
        COMPLETED.labels("failed").inc()
        raise


def listen_for_wakeups() -> None:
    """Use Redis pub/sub to shorten polling delay; reconnect and rely on DB polling."""
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    while not stopping.is_set():
        client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        try:
            with client.pubsub() as pubsub:
                pubsub.subscribe("releaseops:orders")
                while not stopping.is_set():
                    message = pubsub.get_message(timeout=0.5)
                    if message and message["type"] == "message":
                        wake_event.set()
        except redis.RedisError as exc:
            logger.warning(
                "Redis wake listener unavailable; database polling remains active: %s",
                exc,
            )
            stopping.wait(2)
        finally:
            client.close()


def main() -> None:
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    signal.signal(signal.SIGINT, lambda *_: stopping.set())
    start_http_server(8001)
    threading.Thread(
        target=listen_for_wakeups, name="redis-wakeup-listener", daemon=True
    ).start()
    factory = _session_factory(database_url())
    while not stopping.is_set():
        with factory() as session:
            try:
                HEARTBEAT.set(time.time())
                QUEUE_DEPTH.set(
                    session.scalar(
                        select(func.count())
                        .select_from(Order)
                        .where(Order.status == "queued")
                    )
                    or 0
                )
                worked = process_one(session)
            except Exception:
                logger.exception(
                    "Worker loop failed; will retry after the poll interval"
                )
                WORKER_ERRORS.inc()
                session.rollback()
                time.sleep(POLL_SECONDS)
                continue
        if worked is None:
            wake_event.wait(POLL_SECONDS)
            wake_event.clear()


if __name__ == "__main__":
    main()
