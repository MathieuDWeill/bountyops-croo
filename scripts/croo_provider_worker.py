#!/usr/bin/env python3
import asyncio
import os
import sys

# Ensure src/ is in the python path for importing bountyops
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from bountyops.cap_adapter import check_live_dependencies, parse_croo_order
from bountyops.models import RunRequest
from bountyops.orchestrator import run_bountyops


async def main():
    print("Starting CROO Provider Worker...")
    
    # 1. Check live dependencies first
    try:
        sdk, sdk_key, agent_id = check_live_dependencies()
    except (ImportError, ValueError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
        
    # 2. Setup Client
    config = sdk.Config(
        base_url=os.environ.get("CROO_API_URL", "https://api.croo.network"),
        ws_url=os.environ.get("CROO_WS_URL", "wss://api.croo.network/ws"),
        rpc_url=os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
    )
    client = sdk.AgentClient(config, sdk_key)
    
    # 3. Define Callback
    async def on_order_paid(event):
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

        try:
            # Retrieve the full order to make sure we have the payload
            order = await client.get_order(order_id)
            
            try:
                run_request = parse_croo_order(order)
            except ValueError as exc:
                print(f"ERROR: Order {order_id} lacks a compatible payload: {exc}", file=sys.stderr)
                return

            print(f"Running orchestrator for order {order_id}...")
            
            # Run orchestrator
            result = run_bountyops(run_request, order_id=order_id)
            
            # Deliver order
            print(f"Delivering result for order {order_id}...")
            req = {
                "type": sdk.DeliverableType.SCHEMA,
                "value": result.model_dump()
            }
            await client.deliver_order(order_id, req)
            print(f"Successfully delivered result for order {order_id}. Proof hash: {result.proof_hash}")
            
        except Exception as exc:
            print(f"ERROR processing order {order_id}: {exc}", file=sys.stderr)

    async def on_negotiation_created(event):
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
            print(f"Accepting negotiation {negotiation_id}...")
            await client.accept_negotiation(negotiation_id)
            print(f"Successfully accepted negotiation {negotiation_id}")
        except Exception as exc:
            print(f"ERROR accepting negotiation {negotiation_id}: {exc}", file=sys.stderr)

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
