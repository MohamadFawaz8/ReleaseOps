# Lesson 01: API foundation

This milestone gives ReleaseOps a small HTTP service that can be run and inspected locally. The API is a learning foundation; it does not yet process orders.

## Architecture: what runs where

Your editor runs on Windows, while the project commands run in the Ubuntu environment provided by WSL. Uvicorn listens for local HTTP requests and passes them to the FastAPI application. FastAPI matches each request to a route and returns a response.

```text
Browser or curl
      │ HTTP to 127.0.0.1:8000
      ▼
Uvicorn server (WSL Ubuntu)
      ▼
FastAPI app (app/main.py)
```

The eventual project is planned to include a browser frontend, Nginx, an API, a database, a queue, and a worker. Those components will be introduced and tested as separate milestones. They are not part of this initial API.

## Why Python in a web project?

A web application has browser-facing pages and server-side behavior. Python is the language for this project's server-side API and, later, its worker; the browser interface will call that API. Its small, readable service lets us concentrate on building, deploying, monitoring, and troubleshooting software. These DevOps workflows also apply to applications written in other languages.

The infrastructure will run locally on the existing computer to respect the zero-cost, no-card requirement. A local Kubernetes cluster still runs real containers and workloads, but it does not provide hands-on AWS operating experience. AWS networking and managed services will be studied through explicitly labeled design exercises.

## Python and project environment

Ubuntu's system Python is used by operating system tools, so leave it in place. This project targets Python 3.14 in a separate environment managed with `uv`. The `.venv/` directory contains this project's interpreter links and installed packages; it is local generated state and should not be committed.

- `.python-version` selects the project Python version for `uv`.
- `pyproject.toml` declares the project and its direct dependencies and tool settings.
- `uv.lock` records resolved dependency versions so collaborators can reproduce the environment.
- `uv sync --locked` installs the locked environment and fails if the lock needs updating.

Runtime dependencies provide the service: FastAPI defines the API, and Uvicorn serves it over HTTP. Development dependencies support quality checks: pytest runs tests, HTTPX2 supports FastAPI's test client, and Ruff checks and formats code. The lock file improves repeatability, though platform-specific packages can differ across operating systems and architectures.

The initial test run passed with an HTTPX deprecation warning. The installed Starlette version (used by FastAPI) recommends HTTPX2 in its [official test-client documentation](https://www.starlette.io/testclient/), so the development dependency was updated. Read warnings, check the upstream guidance, then verify the replacement rather than hiding the warning.

From the repository root in Ubuntu, synchronize the environment:

```bash
uv sync --locked
```

## Read the application

Open `app/main.py` in your VS Code WSL window. Windows displays the editor, while Python commands run in the Ubuntu project environment.

`from fastapi import FastAPI` imports the framework's application class. `app = FastAPI(...)` creates the application object. Uvicorn will load that object using the reference `app.main:app`: the first `app` names the Python package directory, `main` names the module file, and the final `app` names the object inside that module.

The `@app.get("/")` decorator registers the function below it as the handler for an HTTP GET request to `/`. The function is synchronous and its `dict[str, str]` return annotation says it returns a dictionary whose keys and values are strings. FastAPI serializes that dictionary as JSON for the HTTP response. The root handler returns the service name and version.

The `@app.get("/health")` route similarly returns `{"status": "ok"}`. This is a process responsiveness check only. There is no database, queue, or worker yet, so this endpoint cannot report their readiness. There is also no order workflow yet.

## Start and inspect the service

Start the server from the Ubuntu terminal at the repository root:

```bash
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`uv run` uses the project environment; `--locked` prevents silently changing the resolved environment. Uvicorn imports the module and application object described above. `--host 127.0.0.1` binds only to this computer's loopback interface, so other computers on the network cannot connect. `--port 8000` selects the local TCP port. Keep this terminal open while the server runs.

In a second Ubuntu terminal, request the health route:

```bash
curl -i http://127.0.0.1:8000/health
```

`curl` sends an HTTP request. `-i` includes response headers, which show the status and JSON content type. A successful response has status `200 OK` and body `{"status":"ok"}`.

Compare expected HTTP outcomes:

```bash
curl -i http://127.0.0.1:8000/missing
curl -i -X POST http://127.0.0.1:8000/health
```

The nonexistent route returns `404 Not Found`; the health route exists but does not accept POST, so it returns `405 Method Not Allowed`. These are HTTP error responses, which mean a server answered the request. By contrast, “connection refused” means no server accepted the TCP connection at that address and port. Check the server terminal for startup errors and confirm the URL and port. If port 8000 may already be occupied, inspect listeners with `ss -ltnp`; stop a process only if you recognize it, or select a different port for Uvicorn and curl.

Stop Uvicorn with `Ctrl+C` in its terminal. This sends an interrupt so the development server exits cleanly.

## Run project checks

From the repository root in Ubuntu, run:

```bash
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

Pytest exercises the API's status codes and response contracts. Ruff's `check` reports configured lint issues, and `format --check` reports files that need formatting without changing them. A command's result must be observed before claiming that check passed.

## Recorded verification (2026-10-23)

The assistant verified Python 3.14.9 in Ubuntu 22.04 under WSL, four passing API tests without warnings after the HTTPX2 update, and passing Ruff lint and formatting checks. Live HTTP requests verified GET `/`, `/health`, and `/docs` returning 200, GET `/missing` returning 404, and POST `/health` returning 405. Windows also reached the WSL health route through localhost. The temporary server was stopped cleanly. These checks do not mean the learner exercises below have been completed.

## Exercises

1. Start the service and use `curl -i` to compare `/health`, `/missing`, and POST `/health`. Record each status code and explain what it tells you.
2. Change the root response's version in a local working copy, restart the server, and observe the JSON. Run the test suite and explain how the contract test helps catch an unintended version change. Do not commit this exercise change unless the milestone instructions ask you to.

## Interview questions

1. What is the difference between a `404` response and “connection refused”? What evidence would you inspect first for each?
2. Why does this `/health` response not prove that a future order-processing system is ready to serve traffic?
