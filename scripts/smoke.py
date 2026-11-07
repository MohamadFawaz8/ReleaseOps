#!/usr/bin/env python3
"""Exercise the public order API through the Nginx entry point."""

import json
import os
import time
import urllib.error
import urllib.request

base = os.environ.get("BASE_URL", "http://127.0.0.1:8080")


def request(
    path: str, method: str = "GET", body: dict | None = None, key: str | None = None
):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=8) as response:
        return response.status, json.loads(response.read()) if response.headers.get(
            "Content-Type", ""
        ).startswith("application/json") else response.read().decode()


def expect_conflict(path: str, body: dict, key: str) -> None:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Idempotency-Key": key},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=8)
    except urllib.error.HTTPError as error:
        assert error.code == 409, f"expected 409 conflict, got {error.code}"
        return
    raise AssertionError(
        "reusing an idempotency key with a changed payload must return 409"
    )


status, body = request("/health")
assert status == 200, (status, body)
status, body = request("/ready")
assert status == 200, (status, body)
key = "releaseops-smoke-order"
payload = {"product": "smoke-test", "quantity": 1}
status, created = request("/api/orders", "POST", payload, key)
assert status in (200, 201, 202), (status, created)
order_id = created.get("id") or created.get("order", {}).get("id")
assert order_id is not None, f"missing order id in {created!r}"
duplicate_status, duplicate = request("/api/orders", "POST", payload, key)
duplicate_id = duplicate.get("id") or duplicate.get("order", {}).get("id")
assert duplicate_status in (200, 201, 202) and duplicate_id == order_id, (
    duplicate_status,
    duplicate,
)
expect_conflict("/api/orders", {"product": "changed-payload", "quantity": 1}, key)
deadline = time.monotonic() + 60
while True:
    status, fetched = request(f"/api/orders/{order_id}")
    assert status == 200 and str(order_id) in json.dumps(fetched), (status, fetched)
    if fetched.get("status") == "completed":
        break
    if time.monotonic() >= deadline:
        raise AssertionError(
            f"order {order_id} did not complete in 60 seconds: {fetched}"
        )
    time.sleep(1)
print(
    "PASS health/readiness, idempotency conflict/replay, "
    f"and worker completion via {base}; id={order_id}"
)
