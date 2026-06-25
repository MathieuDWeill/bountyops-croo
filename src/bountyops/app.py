from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

import os
from .cap_adapter import (
    LiveCapAdapter,
    LocalCapAdapter,
    check_live_dependencies,
    get_cap_adapter,
    get_croo_sdk,
    parse_croo_order,
    sanitize_sdk_order,
    resolve_live_order_requirements,
    to_dict,
    safe_serialize,
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
    sdk_key = os.environ.get("CROO_SDK_KEY")
    agent_id = os.environ.get("CROO_AGENT_ID")
    credentials_available = bool(sdk_key and agent_id)
    return {
        "mode": mode,
        "sdk_available": sdk_available,
        "credentials_available": credentials_available,
    }


@app.get("/cap/live/capabilities")
async def cap_live_capabilities() -> dict:
    try:
        sdk, api_key, agent_id = check_live_dependencies()
        adapter = LiveCapAdapter(sdk, api_key, agent_id)
        return await adapter.capabilities()
    except (ImportError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Live CROO SDK error: {exc}")


@app.get("/cap/live/negotiations")
async def cap_live_negotiations(status: str = "pending") -> list:
    adapter = resolve_adapter()
    if not isinstance(adapter, LiveCapAdapter):
        raise HTTPException(status_code=400, detail="Endpoint only available in live mode.")
    try:
        negotiations = await adapter.list_negotiations(status=status)
        return negotiations
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class AcceptDirectRequest(BaseModel):
    provider_fund_address: Optional[str] = None


@app.post("/cap/live/negotiations/{negotiation_id}/accept")
async def cap_live_accept_negotiation(negotiation_id: str) -> dict:
    adapter = resolve_adapter()
    if not isinstance(adapter, LiveCapAdapter):
        raise HTTPException(status_code=400, detail="Endpoint only available in live mode.")
    try:
        await adapter.accept_negotiation(negotiation_id)
        return {"status": "accepted", "negotiation_id": negotiation_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/cap/live/negotiations/{negotiation_id}/accept-direct")
async def cap_live_accept_direct_negotiation(negotiation_id: str, body: Optional[AcceptDirectRequest] = None) -> dict:
    adapter = resolve_adapter()
    if not isinstance(adapter, LiveCapAdapter):
        raise HTTPException(status_code=400, detail="Endpoint only available in live mode.")
    
    fund_address = None
    if body:
        fund_address = body.provider_fund_address
    if not fund_address:
        fund_address = os.environ.get("CROO_PROVIDER_FUND_ADDRESS")
        
    if not fund_address:
        raise HTTPException(
            status_code=400,
            detail="provider_fund_address is required (either in request body or via CROO_PROVIDER_FUND_ADDRESS environment variable)."
        )
        
    try:
        await adapter.accept_negotiation_with_fund_address(negotiation_id, fund_address)
        return {
            "status": "accepted_direct",
            "negotiation_id": negotiation_id,
            "provider_fund_address": fund_address
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/cap/live/orders")
async def cap_live_orders(status: str = "paid") -> list:
    adapter = resolve_adapter()
    if not isinstance(adapter, LiveCapAdapter):
        raise HTTPException(status_code=400, detail="Endpoint only available in live mode.")
    try:
        orders = await adapter.list_orders(status=status)
        return orders
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/cap/live/orders/{order_id}/debug")
async def cap_live_order_debug(order_id: str) -> dict:
    adapter = resolve_adapter()
    if not isinstance(adapter, LiveCapAdapter):
        raise HTTPException(status_code=400, detail="Endpoint only available in live mode.")
    try:
        raw_order = await adapter.client.get_order(order_id)
        sanitized_order = sanitize_sdk_order(raw_order)
        
        linked_negotiation = None
        parse_source = None
        parser_error = None
        
        try:
            _, parse_source, neg = await resolve_live_order_requirements(adapter, order_id, order=raw_order)
            if neg:
                linked_negotiation = sanitize_sdk_order(neg)
        except Exception as e:
            parser_error = str(e)
            
            # Fallback to try finding and retrieving the negotiation regardless of success
            order_dict = to_dict(raw_order)
            negotiation_id = order_dict.get("negotiation_id")
            if not negotiation_id and hasattr(raw_order, "negotiation_id"):
                negotiation_id = getattr(raw_order, "negotiation_id")
                
            if negotiation_id:
                try:
                    neg = await adapter.get_negotiation(negotiation_id)
                    if neg:
                        linked_negotiation = sanitize_sdk_order(neg)
                except Exception:
                    try:
                        negs = await adapter.list_negotiations(status="accepted")
                        for n in negs:
                            n_dict = to_dict(n)
                            n_id = n_dict.get("negotiation_id") or n_dict.get("id")
                            if not n_id and hasattr(n, "negotiation_id"):
                                n_id = getattr(n, "negotiation_id")
                            elif not n_id and hasattr(n, "id"):
                                n_id = getattr(n, "id")
                            
                            if str(n_id) == str(negotiation_id):
                                linked_negotiation = sanitize_sdk_order(n)
                                break
                    except Exception:
                        pass
                        
        return {
            "raw_order": sanitized_order,
            "linked_negotiation": linked_negotiation,
            "parse_source": parse_source,
            "parser_error": parser_error,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/cap/live/orders/{order_id}/pay")
async def cap_live_pay_order(order_id: str) -> dict:
    adapter = resolve_adapter()
    if not isinstance(adapter, LiveCapAdapter):
        raise HTTPException(status_code=400, detail="Endpoint only available in live mode.")
    try:
        res = await adapter.pay_order(order_id)
        return safe_serialize(res)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/cap/live/deliver/{order_id}")
async def cap_live_deliver(order_id: str) -> dict:
    adapter = resolve_adapter()
    if not isinstance(adapter, LiveCapAdapter):
        raise HTTPException(status_code=400, detail="Endpoint only available in live mode.")
    try:
        try:
            run_request, source, neg = await resolve_live_order_requirements(adapter, order_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        
        result = run_bountyops(run_request, order_id=order_id)
        await adapter.deliver_order(order_id, result.model_dump())
        return {"status": "delivered", "order_id": order_id, "proof_hash": result.proof_hash}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/cap/live/run-paid-orders")
async def cap_live_run_paid_orders() -> dict:
    adapter = resolve_adapter()
    if not isinstance(adapter, LiveCapAdapter):
        raise HTTPException(status_code=400, detail="Endpoint only available in live mode.")
    try:
        orders = await adapter.list_orders(status="paid")
        processed = []
        for order in orders:
            order_id = getattr(order, "order_id", None) or getattr(order, "id", None)
            if isinstance(order, dict):
                order_id = order.get("order_id") or order.get("id")
            if not order_id:
                continue
            try:
                run_request, source, neg = await resolve_live_order_requirements(adapter, order_id, order=order)
                result = run_bountyops(run_request, order_id=order_id)
                await adapter.deliver_order(order_id, result.model_dump())
                processed.append(order_id)
            except Exception as exc:
                print(f"Error processing order {order_id} in batch run: {exc}")
        return {"status": "success", "processed_order_ids": processed}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))



@app.get("/capabilities")
async def capabilities() -> dict:
    return await resolve_adapter().capabilities()


@app.post("/quote", response_model=Quote)
async def quote(request: QuoteRequest) -> Quote:
    return await resolve_adapter().quote(request)


@app.post("/orders", response_model=Order)
async def create_order(request: RunRequest) -> Order:
    return await resolve_adapter().create_order(request)


@app.post("/orders/{order_id}/pay", response_model=Order)
async def pay_order(order_id: str) -> Order:
    adapter = resolve_adapter()
    try:
        return await adapter.pay_order(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str) -> Order:
    adapter = resolve_adapter()
    try:
        return await adapter.get_order(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/run", response_model=RunResult)
def run(request: RunRequest) -> RunResult:
    return run_bountyops(request)
