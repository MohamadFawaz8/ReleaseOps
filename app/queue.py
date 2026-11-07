"""Redis wake-up hint. The database polling loop is the durable queue."""

import os

import redis


def wake_worker(order_id: str) -> None:
    client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_timeout=0.2
    )
    try:
        client.publish("releaseops:orders", order_id)
    finally:
        client.close()


def redis_is_ready() -> bool:
    client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_timeout=0.5
    )
    try:
        return bool(client.ping())
    finally:
        client.close()
