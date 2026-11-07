"""Redis wake-up hint. The database polling loop is the durable queue."""

import os

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry


def wake_worker(order_id: str) -> None:
    client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        socket_timeout=0.2,
        socket_connect_timeout=0.2,
        retry=Retry(NoBackoff(), 0),
    )
    try:
        client.publish("releaseops:orders", order_id)
    finally:
        client.close()


def redis_is_ready() -> bool:
    client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        socket_timeout=0.5,
        socket_connect_timeout=0.5,
        retry=Retry(NoBackoff(), 0),
    )
    try:
        return bool(client.ping())
    finally:
        client.close()
