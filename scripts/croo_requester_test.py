#!/usr/bin/env python3
import asyncio
import json
import os
import sys

try:
    import croo
except ImportError:
    print("ERROR: croo-sdk is not installed. Please run: pip install croo-sdk", file=sys.stderr)
    sys.exit(1)


async def run_requester_flow():
    sdk_key = os.environ.get("REQUESTER_CROO_SDK_KEY")
    if not sdk_key:
        print("ERROR: REQUESTER_CROO_SDK_KEY environment variable is required.", file=sys.stderr)
        sys.exit(1)

    service_id = os.environ.get("CROO_TARGET_SERVICE_ID", "5e1f66b4-f39e-4e20-a940-290db013bb8c")
    api_url = os.environ.get("CROO_API_URL", "https://api.croo.network")
    ws_url = os.environ.get("CROO_WS_URL", "wss://api.croo.network/ws")
    rpc_url = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")

    print(f"Initializing CROO client for target service {service_id}...")
    config = croo.Config(
        base_url=api_url,
        ws_url=ws_url,
        rpc_url=rpc_url,
    )
    client = croo.AgentClient(config, sdk_key)

    # BountyOps service requirements
    requirements_dict = {
        "opportunity_title": "CROO Agent Hackathon Opportunity",
        "opportunity_description": "Build a serious, production-grade agent product with real CROO runtime integration.",
        "prize_pool_usd": 10200,
        "deadline": "2026-07-12",
        "builder_profile": "Mathieu. Skills: Python, FastAPI. Goal: build a real CROO product."
    }
    requirements_str = json.dumps(requirements_dict)

    # Optional fund transfer parameters for direct payment testing
    fund_amount = os.environ.get("CROO_FUND_AMOUNT", "")
    fund_token = os.environ.get("CROO_FUND_TOKEN", "")

    req = croo.NegotiateOrderRequest(
        service_id=service_id,
        requirements=requirements_str,
        fund_amount=fund_amount,
        fund_token=fund_token
    )

    print("Negotiating order...")
    negotiation = await client.negotiate_order(req)
    negotiation_id = negotiation.negotiation_id
    print(f"Negotiation created! ID: {negotiation_id}, Status: {negotiation.status}")

    # Wait/list until the order for that negotiation is created.
    print("Waiting/polling until the order is created...")
    order_id = None
    while True:
        negotiation = await client.get_negotiation(negotiation_id)
        print(f"Negotiation status: {negotiation.status}")
        
        if negotiation.status == "rejected":
            print(f"Negotiation rejected! Reason: {negotiation.reject_reason}", file=sys.stderr)
            sys.exit(1)
        elif negotiation.status == "expired":
            print("Negotiation expired!", file=sys.stderr)
            sys.exit(1)
        elif negotiation.status == "accepted":
            print("Negotiation accepted. Finding the order ID...")
            orders = await client.list_orders(croo.ListOptions(role="buyer"))
            for order in orders:
                if order.negotiation_id == negotiation_id:
                    order_id = order.order_id
                    break
            if order_id:
                print(f"Found Order: {order_id}")
                break
            else:
                print("Order not found in listed orders yet. Retrying...")
                
        await asyncio.sleep(5)

    # Retrieve the order details
    order = await client.get_order(order_id)

    # Call pay_order(order_id)
    print(f"Paying order {order_id}...")
    pay_res = await client.pay_order(order_id)
    print("Order payment transaction submitted!")

    # Print order_id, chain_order_id, create_tx_hash, pay_tx_hash
    print("\n--- Transaction Details ---")
    print(f"order_id: {order_id}")
    print(f"chain_order_id: {pay_res.order.chain_order_id or order.chain_order_id}")
    print(f"create_tx_hash: {order.create_tx_hash}")
    print(f"pay_tx_hash: {pay_res.tx_hash}")
    print("---------------------------\n")

    # Poll until paid/completed
    print("Polling order status until completed...")
    while True:
        order = await client.get_order(order_id)
        print(f"Order status: {order.status}")
        if order.status == "completed":
            print("Order completed successfully!")
            break
        elif order.status in ["rejected", "expired", "create_failed", "pay_failed", "deliver_failed"]:
            print(f"Order failed with status: {order.status}", file=sys.stderr)
            if order.reject_reason:
                print(f"Reason: {order.reject_reason}", file=sys.stderr)
            sys.exit(1)
            
        await asyncio.sleep(5)

    # Try get_delivery if completed
    print("Retrieving delivery info...")
    try:
        delivery = await client.get_delivery(order_id)
        print("\n--- Delivery Info ---")
        print(f"Delivery ID: {delivery.delivery_id}")
        print(f"Status: {delivery.status}")
        print(f"Deliverable Type: {delivery.deliverable_type}")
        print(f"Schema Result: {delivery.deliverable_schema}")
        print(f"Text Result: {delivery.deliverable_text}")
        print("---------------------\n")
    except Exception as e:
        print(f"Warning: Could not retrieve delivery details: {e}", file=sys.stderr)

    await client.close()


def main():
    try:
        asyncio.run(run_requester_flow())
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
