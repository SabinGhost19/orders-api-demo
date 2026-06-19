"""Orders API — accepts order line-items, returns the computed total.

Two jobs in the platform demo:

1. ZeroTrustSecret showcase — at startup it reads the DB credentials
   (DB_USERNAME / DB_PASSWORD) that the ZeroTrustSecret injects from Vault and
   logs ONLY whether each is present (never the value). Because the ZTS gates
   injection on requireVerifiedStatus:true, "present=true" is the observable
   proof the supply chain was verified first.

2. GUAC correlation showcase — the image is python:3.11-slim based and pins the
   SAME packages the other Python demo apps use (fastapi/uvicorn like demo-app,
   cryptography==41.0.0 like analytics-worker). Those shared package + CVE nodes
   are what link this app to the others in the Blast Radius graph. The pinned
   deps live in requirements.txt for the SBOM/CVE footprint; this module stays
   dependency-light (fastapi/pydantic) so the unit tests need nothing exotic —
   same convention as analytics-engine-demo.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("orders-api")

app = FastAPI(title="orders-api", version="0.1.0")

ALLOWED_CURRENCIES = {"USD", "EUR", "RON"}


class OrderItem(BaseModel):
    sku: str
    qty: int
    unit_price: int  # minor units (e.g. cents)


class OrderRequest(BaseModel):
    items: list[OrderItem]
    currency: str


class TotalResponse(BaseModel):
    total: int
    currency: str


class OrderResponse(BaseModel):
    order_id: str
    total: int
    currency: str
    status: str
    timestamp: str


def compute_order_total(items: list[OrderItem]) -> int:
    """Pure helper (no I/O), shared by the handlers and the unit tests.

    Sums qty*unit_price across the order; rejects empty orders and any
    non-positive quantity or unit price.
    """
    if not items:
        raise ValueError("order must contain at least one item")
    total = 0
    for item in items:
        if item.qty <= 0:
            raise ValueError("item qty must be positive")
        if item.unit_price <= 0:
            raise ValueError("item unit_price must be positive")
        total += item.qty * item.unit_price
    return total


def _log_secret_presence() -> None:
    """Report (boolean only) whether the ZTS-injected DB creds reached the env."""
    has_user = bool(os.environ.get("DB_USERNAME"))
    has_pass = bool(os.environ.get("DB_PASSWORD"))
    logger.info("orders-api secret check: DB_USERNAME present=%s, DB_PASSWORD present=%s", has_user, has_pass)


_log_secret_presence()


@app.get("/health")
@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orders-api"}


@app.post("/total", response_model=TotalResponse)
def total(payload: OrderRequest) -> TotalResponse:
    if payload.currency not in ALLOWED_CURRENCIES:
        raise HTTPException(status_code=400, detail="unsupported currency")
    try:
        amount = compute_order_total(payload.items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TotalResponse(total=amount, currency=payload.currency)


@app.post("/orders", response_model=OrderResponse)
def create_order(payload: OrderRequest) -> OrderResponse:
    if payload.currency not in ALLOWED_CURRENCIES:
        raise HTTPException(status_code=400, detail="unsupported currency")
    try:
        amount = compute_order_total(payload.items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    now = datetime.now(timezone.utc)
    return OrderResponse(
        order_id="ord-" + now.strftime("%Y%m%d%H%M%S%f"),
        total=amount,
        currency=payload.currency,
        status="accepted",
        timestamp=now.isoformat(),
    )


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
