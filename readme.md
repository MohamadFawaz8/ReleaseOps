# ReleaseOps

ReleaseOps is an order-processing platform built as a hands-on DevOps learning project. The lab is designed to use the learner's existing computer and free local tools: service and software costs remain USD 0, with no credit card, paid plan, or cloud trial required.

## Project goals

The roadmap covers Linux, networking, Git and GitHub, GitHub Actions, CI/CD, a local Jenkins pipeline, Docker, local Kubernetes, Terraform, Nginx, monitoring, security, release management, and Bash/Python. It also includes incident response, runbooks, rollback, backup and restore, and AWS architecture study without provisioning billable AWS resources.

## Implemented

- A small FastAPI service with `GET /` and `GET /health`.
- Automated API contract tests and Ruff lint configuration.
- Python 3.14 selection and a committed dependency lock file.
- A learner-authored GitHub Actions CI workflow for lint, formatting, and API tests on pushes and pull requests targeting `main`, with a manual trigger available. Inspect execution results in the [Actions tab](https://github.com/MohamadFawaz8/ReleaseOps/actions).

Verified on 2026-10-23 in Ubuntu 22.04 under WSL: Python 3.14.9, four passing tests, passing Ruff lint/format checks, live HTTP responses, and Windows-to-WSL localhost access. The temporary verification server was stopped afterward; start the service below to use it.

## Planned

A browser interface, order processing, a database and queue, a local Jenkins pipeline, container packaging, image build/release automation, local Kubernetes deployment, Terraform exercises, Nginx, monitoring, and operational exercises are planned roadmap items. They are not implemented yet. AWS work will be architecture study or local simulation; this project does not provision AWS resources.

## Run locally

Use the Ubuntu terminal in the project root (the folder containing `pyproject.toml`). `uv` manages the Python 3.14 project environment and locked dependencies; `.venv/` is generated locally and ignored by Git. `pyproject.toml` declares project requirements and tool settings, while `uv.lock` records exact dependency versions for repeatable installs.

1. Install `uv` and Python 3.14 if they are not already available. Keep Ubuntu's system Python unchanged; `uv` can install and select a separate project interpreter.
2. From the project root, synchronize the environment from the lock file:

   ```bash
   uv sync --locked
   ```

   This creates/updates `.venv` and fails if `uv.lock` is missing or out of sync with `pyproject.toml`.
3. Start the local development server:

   ```bash
   uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

   `uv run` uses the project environment. `app.main:app` tells Uvicorn to import the object named `app` from `app/main.py`. Binding to `127.0.0.1` limits the listener to the local environment. Port `8000` is where the server listens. For automatic reload while editing, add `--reload` to this command. Windows can normally reach a WSL service through localhost forwarding; custom WSL networking or firewall settings can affect this.
4. Visit `http://127.0.0.1:8000/`, `http://127.0.0.1:8000/health`, and `http://127.0.0.1:8000/docs` in a browser. The first two return JSON; `/docs` shows FastAPI's interactive API documentation. `/health` reports only that the process responds; it does not check database or other dependency readiness.
5. In a second Ubuntu terminal, also in the project root, run the checks:

   ```bash
   uv run --locked pytest -q
   uv run --locked ruff check .
   uv run --locked ruff format --check .
   ```

   Pytest checks the response contracts and HTTP errors. Ruff checks code style and import ordering, and its format check confirms files already follow Ruff's formatter.
6. Stop the server with `Ctrl+C` in the terminal where it is running.

### HTTP exercise

Use `curl -i http://127.0.0.1:8000/health` to inspect both the HTTP status (`200`) and JSON response. Then request a nonexistent path such as `/missing` and observe `404`; use `curl -i -X POST http://127.0.0.1:8000/health` to observe `405` because the endpoint accepts GET. Explain the difference between a server process answering a health request and all downstream dependencies being ready.

### Troubleshooting

- **`uv: command not found`:** `uv` is not installed in this Ubuntu shell or its executable directory is not on `PATH`. Complete the uv installation step, then open a fresh terminal and check `uv --version`.
- **Browser says connection refused:** Check that the server command is still running and that the address uses `127.0.0.1:8000`. A startup traceback means the server did not start; read the first error in that terminal.
- **Port 8000 is already in use:** In Ubuntu, run `ss -ltnp` and look for a listener on port `8000`. Stop the other process if it is yours, or choose another port in the Uvicorn command and browser URL.
- **Missing package or environment mismatch:** From the project root, run `uv sync --locked` again and review any reported lock-file mismatch before retrying the server or checks.
- **uv cannot hardlink files and falls back to copying:** This can happen when the cache is in the Linux filesystem and the project is on a Windows-mounted drive (`/mnt/c`). Copying still installs the packages. If this warning applies to your setup, `uv sync --locked --link-mode=copy` explicitly selects copying.

## Learning evidence

Start with [Lesson 01: API foundation](docs/lessons/01-api-foundation.md) for the architecture, source walkthrough, commands, troubleshooting, and exercises. Continue with [Lesson 02: CI failure and recovery](docs/lessons/02-ci-failure-recovery.md) for the controlled PR exercise and diagnosis. The project brief records the longer roadmap and interview topics. Local coaching notes are intentionally not published.

Application scaffolding and dependency setup use assistant help. Docker, Kubernetes, GitHub Actions, Jenkins, Prometheus, and Grafana are planned as learner-executed milestones with step-by-step guidance, review, and troubleshooting.
