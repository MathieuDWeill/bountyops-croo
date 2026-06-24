from __future__ import annotations

from fastapi import FastAPI, HTTPException

import os
from .cap_adapter import (
    LiveCapAdapter,
    LocalCapAdapter,
    check_live_dependencies,
    get_cap_adapter,
    get_croo_sdk,
)
from .models import Order, Quote, QuoteRequest, RunRequest, RunResult
from .orchestrator import run_bountyops

app = FastAPI(
    title="BountyOps CAP Agent",
    description="Autonomous bounty intelligence and submission procurement agent.",
    version="0.1.0",
)


def resolve_adapter():
    try:
        return get_cap_adapter()
    except (ImportError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent": "BountyOps"}


@app.get("/cap/mode")
def cap_mode() -> dict:
    mode = os.environ.get("CAP_MODE", "mock").lower()
    sdk = get_croo_sdk()
    sdk_available = sdk is not None
    api_key = os.environ.get("CROO_API_KEY")
    agent_id = os.environ.get("CROO_AGENT_ID")
    credentials_available = bool(api_key and agent_id)
    return {
        "mode": mode,
        "sdk_available": sdk_available,
        "credentials_available": credentials_available,
    }


@app.get("/cap/live/capabilities")
def cap_live_capabilities() -> dict:
    try:
        sdk, api_key, agent_id = check_live_dependencies()
        adapter = LiveCapAdapter(sdk, api_key, agent_id)
        return adapter.capabilities()
    except (ImportError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Live CROO SDK error: {exc}")


@app.get("/capabilities")
def capabilities() -> dict:
    return resolve_adapter().capabilities()


@app.post("/quote", response_model=Quote)
def quote(request: QuoteRequest) -> Quote:
    return resolve_adapter().quote(request)


@app.post("/orders", response_model=Order)
def create_order(request: RunRequest) -> Order:
    return resolve_adapter().create_order(request)


@app.post("/orders/{order_id}/pay", response_model=Order)
def pay_order(order_id: str) -> Order:
    adapter = resolve_adapter()
    try:
        return adapter.pay_order(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str) -> Order:
    adapter = resolve_adapter()
    try:
        return adapter.get_order(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc


@app.post("/run", response_model=RunResult)
def run(request: RunRequest) -> RunResult:
    return run_bountyops(request)
