"""HTTP endpoints for the ReleaseOps service."""

from fastapi import FastAPI

app = FastAPI(title="ReleaseOps", version="0.1.0")


@app.get("/")
def read_root() -> dict[str, str]:
    """Return the service identity and version."""
    return {"service": "releaseops", "version": "0.1.0"}


@app.get("/health")
def read_health() -> dict[str, str]:
    """Report process responsiveness; this does not check dependencies."""
    return {"status": "ok"}
