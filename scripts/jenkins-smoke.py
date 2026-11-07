#!/usr/bin/env python3
"""Trigger the local Jenkins pipeline and report its final result safely."""

from __future__ import annotations

import base64
import http.cookiejar
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)

BASE_URL = os.environ.get("JENKINS_URL", "http://127.0.0.1:8081").rstrip("/")
USERNAME = os.environ.get("JENKINS_USERNAME", "releaseops")
PASSWORD_FILE = Path(
    os.environ.get("JENKINS_PASSWORD_FILE", ".secrets/jenkins-admin-password")
)
CONTROLLER_TIMEOUT = 180
BUILD_TIMEOUT = 15 * 60


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_secret() -> str:
    try:
        secret = PASSWORD_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(
            f"Cannot read Jenkins password file {PASSWORD_FILE}: {exc.strerror}"
        ) from None
    if not secret:
        raise RuntimeError(f"Jenkins password file is empty: {PASSWORD_FILE}")
    return secret


class JenkinsClient:
    def __init__(self, password: str) -> None:
        self.password = password
        token = base64.b64encode(f"{USERNAME}:{password}".encode()).decode()
        self.auth_value = f"Basic {token}"
        self.opener = build_opener(
            HTTPCookieProcessor(http.cookiejar.CookieJar()),
            NoRedirectHandler(),
        )

    def request(self, path: str, *, method: str = "GET", data: bytes | None = None):
        headers = {"Authorization": self.auth_value, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(
            urljoin(f"{BASE_URL}/", path.lstrip("/")),
            data=data,
            headers=headers,
            method=method,
        )
        try:
            return self.opener.open(request, timeout=15)
        except HTTPError as exc:
            if exc.code in (201, 302, 303):
                return exc
            raise RuntimeError(
                f"Jenkins returned HTTP {exc.code} for {method} {request.full_url}"
            ) from None
        except URLError as exc:
            reason = getattr(exc, "reason", "connection failed")
            raise RuntimeError(
                f"Cannot reach Jenkins at {BASE_URL}: {reason}"
            ) from None

    def json(self, path: str) -> dict:
        with self.request(path) as response:
            return json.loads(response.read())

    def safe_text(self, path: str) -> str:
        with self.request(path) as response:
            return response.read().decode("utf-8", errors="replace")


def wait_for_controller(client: JenkinsClient) -> None:
    deadline = time.monotonic() + CONTROLLER_TIMEOUT
    last_error = "controller has not responded"
    while time.monotonic() < deadline:
        try:
            client.json("api/json?tree=mode")
            return
        except (RuntimeError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            time.sleep(3)
    raise RuntimeError(
        f"Jenkins controller did not become ready within {CONTROLLER_TIMEOUT}s: "
        f"{last_error}"
    )


def wait_for_agent(client: JenkinsClient) -> None:
    deadline = time.monotonic() + CONTROLLER_TIMEOUT
    last_status = "agent node not found"
    while time.monotonic() < deadline:
        try:
            payload = client.json(
                "computer/api/json?tree=computer[displayName,offline,temporarilyOffline,offlineCauseReason]"
            )
            for computer in payload.get("computer", []):
                if computer.get("displayName") == "releaseops-agent":
                    if not computer.get("offline") and not computer.get(
                        "temporarilyOffline"
                    ):
                        return
                    last_status = (
                        computer.get("offlineCauseReason") or "agent is offline"
                    )
        except (RuntimeError, json.JSONDecodeError) as exc:
            last_status = str(exc)
        time.sleep(3)
    raise RuntimeError(
        f"Jenkins agent did not come online within {CONTROLLER_TIMEOUT}s: {last_status}"
    )


def trigger_build_with_crumb(client: JenkinsClient) -> str:
    crumb = client.json("crumbIssuer/api/json")
    field = crumb.get("crumbRequestField")
    value = crumb.get("crumb")
    data = urlencode({"DEPLOY_PREVIEW": "true"}).encode()
    headers = {field: value} if field and value else {}
    request = Request(
        f"{BASE_URL}/job/releaseops-ci/buildWithParameters",
        data=data,
        headers={
            "Authorization": client.auth_value,
            "Content-Type": "application/x-www-form-urlencoded",
            **headers,
        },
        method="POST",
    )
    try:
        response = client.opener.open(request, timeout=15)
    except HTTPError as exc:
        if exc.code != 201:
            raise RuntimeError(
                f"Jenkins build trigger returned HTTP {exc.code}"
            ) from None
        response = exc
    except URLError as exc:
        raise RuntimeError(
            "Jenkins build trigger failed: "
            f"{getattr(exc, 'reason', 'connection failed')}"
        ) from None
    location = response.headers.get("Location")
    if not location:
        raise RuntimeError("Jenkins accepted no queue location for the triggered build")
    return urljoin(f"{BASE_URL}/", location)


def wait_for_build(client: JenkinsClient, queue_url: str) -> tuple[str, int, str]:
    queue_api = urljoin(queue_url.rstrip("/") + "/", "api/json")
    deadline = time.monotonic() + BUILD_TIMEOUT
    build_url = ""
    build_number = 0
    while time.monotonic() < deadline:
        try:
            queue_item = client.json(queue_api)
        except RuntimeError:
            time.sleep(3)
            continue
        executable = queue_item.get("executable")
        if executable:
            build_url = executable.get("url", "")
            build_number = int(executable.get("number", 0))
            break
        if queue_item.get("cancelled"):
            raise RuntimeError("Jenkins cancelled the queued releaseops-ci build")
        time.sleep(3)
    if not build_url:
        raise RuntimeError(
            "Jenkins did not assign an executor within the build timeout"
        )

    while time.monotonic() < deadline:
        build = client.json(urljoin(build_url.rstrip("/") + "/", "api/json"))
        if not build.get("building", True):
            return build_url, build_number, str(build.get("result", "UNKNOWN"))
        time.sleep(5)
    raise RuntimeError(
        f"Jenkins build {build_number} exceeded the {BUILD_TIMEOUT}s timeout"
    )


def sanitized_console_tail(client: JenkinsClient, build_url: str) -> str:
    try:
        log = client.safe_text(urljoin(build_url.rstrip("/") + "/", "consoleText"))
    except RuntimeError as exc:
        return f"Unable to retrieve Jenkins console log: {exc}"
    log = log.replace(client.password, "[REDACTED]")
    log = log.replace(client.auth_value, "[REDACTED AUTH]")
    log = re.sub(r"(?i)(authorization\s*[:=]\s*)(?:basic\s+)?\S+", r"\1[REDACTED]", log)
    log = re.sub(r"(?i)((?:password|passwd|secret)\s*[:=]\s*)\S+", r"\1[REDACTED]", log)
    return "\n".join(log.splitlines()[-80:])


def main() -> int:
    password = read_secret()
    client = JenkinsClient(password)
    try:
        wait_for_controller(client)
        wait_for_agent(client)
        queue_url = trigger_build_with_crumb(client)
        build_url, number, result = wait_for_build(client, queue_url)
        print(f"Jenkins build #{number}: {build_url} — {result}")
        if result != "SUCCESS":
            print("Sanitized Jenkins console tail:")
            print(sanitized_console_tail(client, build_url))
            return 1
        print(
            "PASS: Jenkins controller, agent, and parameterized local preview "
            "pipeline completed successfully."
        )
        return 0
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
