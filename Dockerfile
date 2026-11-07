FROM python:3.14.9-alpine3.24 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
ENV PATH="/app/.venv/bin:${PATH}"

# Apply available distribution security fixes; installers are unnecessary at runtime.
RUN apk upgrade --no-cache && \
    /usr/local/bin/python -m pip uninstall --yes pip && \
    rm -rf /usr/local/lib/python3.14/ensurepip && \
    addgroup -g 10001 appuser && adduser -D -u 10001 -G appuser appuser

FROM base AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=0
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-cache

FROM dependencies AS dev-test
RUN uv sync --locked --no-cache && chown -R appuser:appuser /app
COPY app/ ./app/
COPY tests/ ./tests/
USER appuser
CMD ["/app/.venv/bin/pytest", "-q"]

FROM base AS runtime
COPY --from=dependencies /app/.venv /app/.venv
COPY app/ ./app/
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
