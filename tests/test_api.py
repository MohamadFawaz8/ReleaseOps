"""Isolated HTTP and worker checks; no Docker or external services are required."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import get_session
from app.main import app
from app.models import Base


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'orders.db'}")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(db_factory) -> Generator[TestClient, None, None]:
    def override_session():
        with db_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_root_and_health_keep_original_contract(client: TestClient) -> None:
    assert client.get("/").json() == {"service": "releaseops", "version": "0.1.0"}
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize(
    "body",
    [
        {"product": "", "quantity": 1},
        {"product": "pen", "quantity": 0},
        {"product": "pen", "quantity": 1.2},
        {"product": "x" * 121, "quantity": 1},
    ],
)
def test_order_input_validation(client: TestClient, body: dict) -> None:
    assert client.post("/api/orders", json=body).status_code == 422


def test_large_json_body_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/orders",
        json={"product": "pen", "quantity": 1, "unused": "x" * 9000},
    )
    assert response.status_code == 413


def test_create_list_get_and_unknown_order(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.main.wake_worker", lambda _order_id: None)
    created = client.post(
        "/api/orders", json={"product": "blue notebook", "quantity": 2}
    )
    assert created.status_code == 202
    order = created.json()
    assert order["status"] == "queued"
    assert client.get("/api/orders").json()[0]["id"] == order["id"]
    assert client.get(f"/api/orders/{order['id']}").json() == order
    assert (
        client.get("/api/orders/00000000-0000-0000-0000-000000000000").status_code
        == 404
    )


def test_idempotency_duplicate_and_conflict(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.main.wake_worker", lambda _order_id: None)
    headers = {"Idempotency-Key": "retry-123"}
    payload = {"product": "pen", "quantity": 3}
    first = client.post("/api/orders", json=payload, headers=headers)
    duplicate = client.post("/api/orders", json=payload, headers=headers)
    conflict = client.post(
        "/api/orders", json={"product": "pen", "quantity": 4}, headers=headers
    )
    assert first.status_code == duplicate.status_code == 202
    assert first.json()["id"] == duplicate.json()["id"]
    assert conflict.status_code == 409


def test_idempotency_duplicate_compares_normalized_product(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr("app.main.wake_worker", lambda _order_id: None)
    headers = {"Idempotency-Key": "whitespace-retry"}
    first = client.post(
        "/api/orders", json={"product": "pen", "quantity": 1}, headers=headers
    )
    duplicate = client.post(
        "/api/orders", json={"product": " pen ", "quantity": 1}, headers=headers
    )
    assert first.status_code == duplicate.status_code == 202
    assert first.json()["id"] == duplicate.json()["id"]


def test_redis_publish_failure_does_not_lose_committed_order(
    client: TestClient, monkeypatch
) -> None:
    def unavailable(_order_id: str) -> None:
        raise ConnectionError("redis offline")

    monkeypatch.setattr("app.main.wake_worker", unavailable)
    response = client.post("/api/orders", json={"product": "mug", "quantity": 1})
    assert response.status_code == 202
    assert (
        client.get(f"/api/orders/{response.json()['id']}").json()["status"] == "queued"
    )


def test_readiness_checks_database_and_redis(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.main.redis_is_ready", lambda: True)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok", "redis": "ok"}
    monkeypatch.setattr("app.main.redis_is_ready", lambda: False)
    assert client.get("/ready").status_code == 503


def test_worker_recovers_stale_claim_and_completes(db_factory, monkeypatch) -> None:
    from datetime import UTC, datetime, timedelta

    from app import worker
    from app.models import Order

    monkeypatch.setattr(worker, "PROCESS_SECONDS", 0)
    monkeypatch.setattr(worker, "LEASE_SECONDS", 300)
    with db_factory() as session:
        stale = Order(
            product="stale",
            quantity=1,
            status="processing",
            claimed_at=datetime.now(UTC) - timedelta(minutes=10),
        )
        session.add(stale)
        session.commit()
        order_id = worker.process_one(session)
        assert order_id == stale.id
        session.refresh(stale)
        assert stale.status == "completed"


def test_worker_records_processing_failure(db_factory, monkeypatch) -> None:
    from app import worker
    from app.models import Order

    monkeypatch.setattr(worker, "PROCESS_SECONDS", 1)
    monkeypatch.setattr(
        worker.stopping,
        "wait",
        lambda _seconds: (_ for _ in ()).throw(RuntimeError("synthetic failure")),
    )
    with db_factory() as session:
        order = Order(product="test failure", quantity=1)
        session.add(order)
        session.commit()
        with pytest.raises(RuntimeError, match="synthetic failure"):
            worker.process_one(session)
        session.refresh(order)
        assert order.status == "failed"


def test_metrics_endpoint_has_prometheus_content_type(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "releaseops_order_requests_total" in response.text
    assert "text/plain" in response.headers["content-type"]
