#!/usr/bin/env python3
"""Verify the provisioned Prometheus, Grafana, and Alertmanager stack."""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090").rstrip("/")
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://grafana:3000").rstrip("/")
ALERTMANAGER_URL = os.environ.get(
    "ALERTMANAGER_URL", "http://alertmanager:9093"
).rstrip("/")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "")
TIMEOUT_SECONDS = 120


def fetch(url: str, *, username: str | None = None, password: str | None = None):
    headers = {"Accept": "application/json"}
    if username is not None and password is not None:
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=8) as response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "")
        return (
            json.loads(body)
            if "json" in content_type
            else body.decode("utf-8", errors="replace")
        )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_once() -> list[str]:
    checks: list[str] = []

    targets = fetch(f"{PROMETHEUS_URL}/api/v1/targets?state=active")
    require(
        targets.get("status") == "success",
        "Prometheus target API did not return success",
    )
    active = targets.get("data", {}).get("activeTargets", [])
    by_job = {target.get("labels", {}).get("job"): target for target in active}
    for job in ("releaseops-api", "releaseops-worker"):
        target = by_job.get(job)
        require(target is not None, f"Prometheus target {job} is missing")
        require(
            target.get("health") == "up",
            f"Prometheus target {job} is {target.get('health')}",
        )
    checks.append("Prometheus API and worker targets are up")

    rules = fetch(f"{PROMETHEUS_URL}/api/v1/rules?type=alert")
    require(
        rules.get("status") == "success", "Prometheus rules API did not return success"
    )
    groups = rules.get("data", {}).get("groups", [])
    group = next(
        (item for item in groups if item.get("name") == "releaseops-service"), None
    )
    require(group is not None, "ReleaseOps alert rule group is missing")
    alert_rules = group.get("rules", [])
    require(
        len(alert_rules) >= 6,
        f"Expected at least six loaded alerts, found {len(alert_rules)}",
    )
    require(
        all(rule.get("health") == "ok" for rule in alert_rules),
        "At least one ReleaseOps alert rule is unhealthy",
    )
    checks.append(f"Prometheus loaded {len(alert_rules)} healthy ReleaseOps alerts")

    grafana_health = fetch(f"{GRAFANA_URL}/api/health")
    require(grafana_health.get("database") == "ok", "Grafana database is not healthy")
    datasource = fetch(
        f"{GRAFANA_URL}/api/datasources/uid/prometheus",
        username=GRAFANA_USER,
        password=GRAFANA_PASSWORD,
    )
    require(
        datasource.get("uid") == "prometheus",
        "Grafana Prometheus data source UID is missing",
    )
    dashboard_response = fetch(
        f"{GRAFANA_URL}/api/dashboards/uid/releaseops-local",
        username=GRAFANA_USER,
        password=GRAFANA_PASSWORD,
    )
    dashboard = dashboard_response.get("dashboard", {})
    require(
        dashboard.get("uid") == "releaseops-local",
        "Grafana ReleaseOps dashboard UID is missing",
    )
    panels = dashboard.get("panels", [])
    require(len(panels) == 6, f"Expected six Grafana panels, found {len(panels)}")
    checks.append(
        "Grafana database, authenticated data source, and six-panel dashboard "
        "are healthy"
    )

    alertmanager = fetch(f"{ALERTMANAGER_URL}/api/v2/status")
    require(isinstance(alertmanager, dict), "Alertmanager status response is not JSON")
    checks.append("Alertmanager API is responding")
    return checks


def main() -> int:
    if not GRAFANA_PASSWORD:
        print(
            "FAIL: GRAFANA_PASSWORD environment variable is required", file=sys.stderr
        )
        return 1
    deadline = time.monotonic() + TIMEOUT_SECONDS
    last_error = "monitoring services are still starting"
    while time.monotonic() < deadline:
        try:
            for check in verify_once():
                print(f"PASS: {check}")
            return 0
        except (
            HTTPError,
            URLError,
            TimeoutError,
            json.JSONDecodeError,
            RuntimeError,
        ) as exc:
            last_error = f"{type(exc).__name__}: {getattr(exc, 'reason', str(exc))}"
            time.sleep(5)
    print(
        f"FAIL: monitoring stack did not become healthy within {TIMEOUT_SECONDS}s: "
        f"{last_error}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
