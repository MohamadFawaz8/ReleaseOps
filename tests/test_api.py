"""Contract checks for the initial HTTP API."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_service_identity() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"service": "releaseops", "version": "0.1.0"}
    assert response.headers["content-type"].startswith("application/json")


def test_health_reports_responsive_process() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")


def test_unknown_path_returns_not_found() -> None:
    response = client.get("/missing")

    assert response.status_code == 404


def test_health_rejects_write_method() -> None:
    response = client.post("/health")

    assert response.status_code == 405
