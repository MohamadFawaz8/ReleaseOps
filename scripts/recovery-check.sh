#!/usr/bin/env bash
# Non-destructive local dependency outage and recovery check; adds one synthetic order.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
resume() { docker compose start redis worker >/dev/null 2>&1 || true; }
trap resume EXIT
docker compose exec -T api python -c \
  'import urllib.request; urllib.request.urlopen("http://web:8080/ready", timeout=5)'
docker compose stop worker redis
order_id="$(docker compose exec -T api python - <<'PY'
import json
import urllib.error
import urllib.request
import uuid

base = "http://web:8080"
with urllib.request.urlopen(base + "/health", timeout=5) as response:
    assert response.status == 200
try:
    urllib.request.urlopen(base + "/ready", timeout=5)
except urllib.error.HTTPError as error:
    assert error.code == 503
else:
    raise AssertionError("readiness must fail when Redis is stopped")
request = urllib.request.Request(
    base + "/api/orders",
    data=json.dumps({"product": "recovery-check", "quantity": 1}).encode(),
    headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
)
with urllib.request.urlopen(request, timeout=10) as response:
    order = json.load(response)
    assert response.status == 202 and order["status"] == "queued"
    print(order["id"])
PY
)"
docker compose start worker
docker compose exec -T -e ORDER_ID="$order_id" api python - <<'PY'
import json
import os
import time
import urllib.request

deadline = time.monotonic() + 60
while time.monotonic() < deadline:
    with urllib.request.urlopen(
        "http://web:8080/api/orders/" + os.environ["ORDER_ID"], timeout=8
    ) as response:
        order = json.load(response)
    if order["status"] == "completed":
        print("PASS: durable order completed while Redis was unavailable")
        break
    time.sleep(1)
else:
    raise AssertionError("database polling did not recover the queued order")
PY
docker compose start redis
for attempt in $(seq 1 30); do
  if docker compose exec -T api python -c \
    'import urllib.request; urllib.request.urlopen("http://web:8080/ready", timeout=5)' 2>/dev/null; then
    printf 'PASS: readiness recovered; synthetic order %s\n' "$order_id"
    exit 0
  fi
  sleep 1
done
echo 'Readiness did not recover; inspect api/redis logs.' >&2
exit 1
