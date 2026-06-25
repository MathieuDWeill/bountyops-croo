#!/usr/bin/env python3
import asyncio
import dataclasses
import json
import os
import sys

# Ensure src/ is in the python path for importing bountyops
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from bountyops.cap_adapter import (
    check_live_dependencies,
    parse_croo_order,
    resolve_live_order_requirements,
    LiveCapAdapter,
)
from bountyops.models import RunRequest
from bountyops.orchestrator import run_bountyops


def serialize_dataclass_or_dict(x):
    if x is None:
        return None
    if isinstance(x, dict):
        return x
    if dataclasses.is_dataclass(x):
        return dataclasses.asdict(x)
    if hasattr(x, "model_dump") and callable(x.model_dump):
        return x.model_dump()
    if hasattr(x, "dict") and callable(x.dict):
        return x.dict()
    from bountyops.cap_adapter import safe_serialize
    serialized = safe_serialize(x)
    if isinstance(serialized, dict):
        return serialized
    return {}


async def handle_negotiation_created(event, client):
    print(f"Received EventType.NEGOTIATION_CREATED: {event}")
    negotiation_id = None
    if isinstance(event, dict):
        negotiation_id = event.get("negotiation_id") or event.get("id")
    else:
        negotiation_id = getattr(event, "negotiation_id", None) or getattr(event, "id", None)
        
    if not negotiation_id:
        print("ERROR: Event lacks negotiation_id or id.", file=sys.stderr)
        return

    try:
        negotiation = await client.get_negotiation(negotiation_id)
        
        direct_accept_env = os.environ.get("CROO_DIRECT_ACCEPT", "").lower() == "true"
        is_direct = direct_accept_env
            
        if is_direct:
            provider_fund_address = os.environ.get("CROO_PROVIDER_FUND_ADDRESS")
            if not provider_fund_address:
                raise ValueError("CROO_PROVIDER_FUND_ADDRESS environment variable is required for direct fund-transfer accept.")
            print("Using direct fund-transfer accept")
            await client.accept_negotiation_with_fund_address(negotiation_id, provider_fund_address)
            print(f"Successfully accepted negotiation {negotiation_id} via direct fund-transfer mode")
        else:
            print("Using standard accept")
            await client.accept_negotiation(negotiation_id)
            print(f"Successfully accepted negotiation {negotiation_id} via normal mode")
    except Exception as exc:
        print(f"ERROR accepting negotiation {negotiation_id}: {exc}", file=sys.stderr)


async def handle_order_paid(event, adapter):
    # Extract order details
    print(f"Received EventType.ORDER_PAID: {event}")
    order_id = None
    if isinstance(event, dict):
        order_id = event.get("order_id") or event.get("id")
    else:
        order_id = getattr(event, "order_id", None) or getattr(event, "id", None)
        
    if not order_id:
        print("ERROR: Event lacks order_id or id.", file=sys.stderr)
        return

    parse_source = None
    parser_error = None
    try:
        run_request, parse_source, neg = await resolve_live_order_requirements(adapter, order_id)
        print(f"Successfully resolved requirements. parse_source: {parse_source}")
    except Exception as exc:
        parser_error = str(exc)
        print(f"ERROR: Failed to resolve requirements for order {order_id}. parser_error: {parser_error}", file=sys.stderr)
        return

    try:
        print(f"Running orchestrator for order {order_id}...")
        
        # Run orchestrator
        result = run_bountyops(run_request, order_id=order_id)
        
        # Deliver order
        print(f"Delivering result for order {order_id}...")
        
        serialized_result = serialize_dataclass_or_dict(result)
        
        # Build the flat delivery schema required by the Agent Store
        submission_pack_dict = serialized_result.get("submission_pack") or {}
        go_no_go = submission_pack_dict.get("go_no_go") or "MAYBE"
        expected_value_score = submission_pack_dict.get("expected_value_score") or 0
        recommended_project = submission_pack_dict.get("recommended_project") or ""
        proof_hash = serialized_result.get("proof_hash") or ""
        
        try:
            expected_value_score = float(expected_value_score)
        except (TypeError, ValueError):
            expected_value_score = 0.0
            
        flat_payload = {
            "go_no_go": str(go_no_go),
            "expected_value_score": expected_value_score,
            "recommended_project": str(recommended_project),
            "proof_hash": str(proof_hash),
            "submission_pack": json.dumps(serialized_result)
        }
        
        schema_json = json.dumps(flat_payload)
        req = adapter.sdk.DeliverOrderRequest(
            deliverable_type=adapter.sdk.DeliverableType.SCHEMA,
            deliverable_schema=schema_json,
            deliverable_text=""
        )
        
        await adapter.client.deliver_order(order_id, req)
        print(f"Successfully delivered result for order {order_id}. Proof hash: {result.proof_hash}")
        
    except Exception as exc:
        print(f"ERROR processing order {order_id}: {exc}", file=sys.stderr)


async def main():
    print("Starting CROO Provider Worker...")
    
    # 1. Check live dependencies first
    try:
        sdk, sdk_key, agent_id = check_live_dependencies()
    except (ImportError, ValueError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
        
    # 2. Setup Adapter and Client
    adapter = LiveCapAdapter(sdk, sdk_key, agent_id)
    client = adapter.client
    
    # 3. Define Callback and Task Scheduling Helper
    def safe_schedule(coro, event_name):
        task = asyncio.create_task(coro)
        print(f"Scheduled task for {event_name}")
        def handle_result(t):
            try:
                t.result()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Exception raised in scheduled task for {event_name}: {e}", file=sys.stderr)
        task.add_done_callback(handle_result)

    async def process_order_paid(event):
        await handle_order_paid(event, adapter)

    def on_order_paid(event):
        safe_schedule(process_order_paid(event), "ORDER_PAID")

    def on_negotiation_created(event):
        safe_schedule(handle_negotiation_created(event, client), "NEGOTIATION_CREATED")

    # 4. Connect websocket and attach listeners
    print("Connecting to CROO WebSocket...")
    stream = await client.connect_websocket()
    
    # Listen to EventType.ORDER_PAID and EventType.NEGOTIATION_CREATED
    stream.on(sdk.EventType.ORDER_PAID, on_order_paid)
    stream.on(sdk.EventType.NEGOTIATION_CREATED, on_negotiation_created)
    print("Worker is listening for NEGOTIATION_CREATED and ORDER_PAID events. Press Ctrl+C to stop.")
    
    # Keep the event loop running
    while True:
        await asyncio.sleep(3600)



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorker stopped by user.")
        sys.exit(0)
