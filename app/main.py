"""ReleaseOps HTTP API. PostgreSQL is authoritative; Redis is only a wake hint."""

import os
import time
from datetime import datetime
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Order
from app.queue import redis_is_ready, wake_worker
from app.request_limit import RequestSizeLimitMiddleware

app = FastAPI(title="ReleaseOps", version=os.getenv("APP_VERSION", "0.1.0"))
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=8192)
REQUESTS = Counter(
    "releaseops_order_requests_total", "Order submission requests", ["result"]
)
HTTP_DURATION = Histogram(
    "releaseops_http_request_duration_seconds",
    "HTTP request duration",
    ["route", "method"],
)
REDIS_WAKE_FAILURES = Counter(
    "releaseops_redis_wake_failures_total",
    "Redis wake-up messages that could not be published",
)
KNOWN_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class OrderInput(BaseModel):
    product: str = Field(min_length=1, max_length=120, pattern=r".*\S.*")
    quantity: int = Field(gt=0, le=10000, strict=True)


class OrderOutput(BaseModel):
    id: UUID
    product: str
    quantity: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


@app.middleware("http")
async def limit_request_body(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    route_name = getattr(route, "path", "unmatched")
    method = request.method if request.method in KNOWN_METHODS else "OTHER"
    HTTP_DURATION.labels(route_name, method).observe(time.perf_counter() - started)
    return response


@app.get("/")
def read_root() -> dict[str, str]:
    return {"service": "releaseops", "version": os.getenv("APP_VERSION", "0.1.0")}


@app.get("/health")
def read_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError:
        db_ok = False
    try:
        redis_ok = redis_is_ready()
    except Exception:
        redis_ok = False
    if not db_ok or not redis_ok:
        raise HTTPException(
            status_code=503, detail={"database": db_ok, "redis": redis_ok}
        )
    return {"status": "ready", "database": "ok", "redis": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/orders", response_model=OrderOutput, status_code=202)
def create_order(
    payload: OrderInput,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", max_length=128
    ),
    session: Session = Depends(get_session),
) -> Order:
    normalized_product = payload.product.strip()
    if idempotency_key is not None and (
        not idempotency_key.strip() or len(idempotency_key) > 128
    ):
        raise HTTPException(
            status_code=422, detail="Idempotency-Key must contain 1 to 128 characters"
        )
    if idempotency_key:
        existing = session.scalar(
            select(Order).where(Order.idempotency_key == idempotency_key)
        )
        if existing:
            if (existing.product, existing.quantity) != (
                normalized_product,
                payload.quantity,
            ):
                REQUESTS.labels("conflict").inc()
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency-Key was already used with a different order",
                )
            REQUESTS.labels("duplicate").inc()
            return existing
    order = Order(
        product=normalized_product,
        quantity=payload.quantity,
        idempotency_key=idempotency_key,
    )
    session.add(order)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = (
            session.scalar(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
            if idempotency_key
            else None
        )
        if existing and (existing.product, existing.quantity) == (
            normalized_product,
            payload.quantity,
        ):
            REQUESTS.labels("duplicate").inc()
            return existing
        REQUESTS.labels("conflict").inc()
        raise HTTPException(
            status_code=409, detail="Idempotency-Key was already used"
        ) from None
    session.refresh(order)
    REQUESTS.labels("accepted").inc()
    try:
        wake_worker(str(order.id))
    except Exception:
        # Commit already succeeded. The polling worker will still discover this row.
        REDIS_WAKE_FAILURES.inc()
    return order


@app.get("/api/orders", response_model=list[OrderOutput])
def list_orders(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[Order]:
    return list(
        session.scalars(
            select(Order).order_by(Order.created_at.desc(), Order.id).limit(limit)
        )
    )


@app.get("/api/orders/{order_id}", response_model=OrderOutput)
def get_order(order_id: UUID, session: Session = Depends(get_session)) -> Order:
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
