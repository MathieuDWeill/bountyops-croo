from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta

from .models import LedgerEvent, Order, OrderStatus, Quote, QuoteRequest, RunRequest
from .orchestrator import run_bountyops



class LocalCapAdapter:
    """Small local adapter that mirrors the lifecycle of a paid CAP-callable agent.

    This is intentionally simple so reviewers can run it without chain credentials.
    Replace this class with live CROO SDK calls when using a production Agent Store listing.
    """

    def __init__(self):
        self.orders: dict[str, Order] = {}

    def capabilities(self) -> dict:
        return {
            "agent": "BountyOps",
            "wallet": "0xBountyOpsAgent",
            "services": [
                {
                    "id": "opportunity_to_submission_pack",
                    "price_usdc": 25.0,
                    "description": "Scout, score, design, draft, and verify a builder opportunity submission pack.",
                    "deliverables": ["submission_pack", "cap_order_ledger", "proof_hash"],
                },
                {
                    "id": "roi_scan",
                    "price_usdc": 5.0,
                    "description": "Rank a paid opportunity by expected value and effort.",
                    "deliverables": ["go_no_go", "score", "rationale"],
                },
            ],
            "counterparty_agents": [
                "OpportunityScoutAgent",
                "ROIScorerAgent",
                "AgentDesignerAgent",
                "SubmissionWriterAgent",
                "VerifierAgent",
            ],
        }

    def quote(self, request: QuoteRequest) -> Quote:
        return Quote(
            price_usdc=25.0,
            expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            deliverables=["submission_pack", "specialist_order_ledger", "proof_hash"],
        )

    def create_order(self, request: RunRequest) -> Order:
        quote = self.quote(QuoteRequest(**request.model_dump()))
        order = Order(quote=quote, request=request)
        order.ledger.append(LedgerEvent(actor="Buyer", action="order_created", counterparty="BountyOps"))
        self.orders[order.order_id] = order
        return order

    def pay_order(self, order_id: str) -> Order:
        order = self.orders[order_id]
        order.status = OrderStatus.PAID
        order.ledger.append(
            LedgerEvent(actor="Buyer", action="order_paid", counterparty="BountyOps", amount_usdc=order.quote.price_usdc)
        )
        order.status = OrderStatus.IN_PROGRESS
        result = run_bountyops(order.request, order_id=order.order_id)
        order.result = result
        order.status = OrderStatus.COMPLETED
        order.ledger.extend(result.ledger)
        return order

    def get_order(self, order_id: str) -> Order:
        return self.orders[order_id]


def get_croo_sdk():
    """Helper to dynamically import or check for the croo module."""
    if "croo" in sys.modules:
        return sys.modules["croo"]
    try:
        import croo
        return croo
    except ImportError:
        return None


def check_live_dependencies():
    """Checks if the CROO SDK and credentials are present.
    Raises ImportError or ValueError if they are missing.
    """
    sdk = get_croo_sdk()
    if sdk is None:
        raise ImportError("CROO SDK (croo module) is missing.")
    api_key = os.environ.get("CROO_API_KEY")
    agent_id = os.environ.get("CROO_AGENT_ID")
    if not api_key or not agent_id:
        raise ValueError("CROO credentials (CROO_API_KEY, CROO_AGENT_ID) are missing.")
    return sdk, api_key, agent_id


class LiveCapAdapter:
    """Live CAP Adapter that delegates to the live CROO SDK."""

    def __init__(self, sdk, api_key: str, agent_id: str):
        self.sdk = sdk
        self.api_key = api_key
        self.agent_id = agent_id

        # Attempt to initialize a client if the SDK exposes Client, Croo, or SDK classes
        if hasattr(sdk, "Client"):
            self.client = sdk.Client(api_key=api_key, agent_id=agent_id)
        elif hasattr(sdk, "Croo"):
            self.client = sdk.Croo(api_key=api_key, agent_id=agent_id)
        elif hasattr(sdk, "SDK"):
            self.client = sdk.SDK(api_key=api_key, agent_id=agent_id)
        else:
            self.client = None

    def capabilities(self) -> dict:
        if self.client and hasattr(self.client, "capabilities"):
            return self.client.capabilities()
        if hasattr(self.sdk, "get_capabilities"):
            return self.sdk.get_capabilities(api_key=self.api_key, agent_id=self.agent_id)
        raise AttributeError("CROO SDK does not implement capabilities/get_capabilities.")

    def quote(self, request: QuoteRequest) -> Quote:
        if self.client and hasattr(self.client, "quote"):
            return self.client.quote(request)
        if hasattr(self.sdk, "quote"):
            return self.sdk.quote(request, api_key=self.api_key, agent_id=self.agent_id)
        raise AttributeError("CROO SDK does not implement quote.")

    def create_order(self, request: RunRequest) -> Order:
        if self.client and hasattr(self.client, "create_order"):
            return self.client.create_order(request)
        if hasattr(self.sdk, "create_order"):
            return self.sdk.create_order(request, api_key=self.api_key, agent_id=self.agent_id)
        raise AttributeError("CROO SDK does not implement create_order.")

    def pay_order(self, order_id: str) -> Order:
        if self.client and hasattr(self.client, "pay_order"):
            return self.client.pay_order(order_id)
        if hasattr(self.sdk, "pay_order"):
            return self.sdk.pay_order(order_id, api_key=self.api_key, agent_id=self.agent_id)
        raise AttributeError("CROO SDK does not implement pay_order.")

    def get_order(self, order_id: str) -> Order:
        if self.client and hasattr(self.client, "get_order"):
            return self.client.get_order(order_id)
        if hasattr(self.sdk, "get_order"):
            return self.sdk.get_order(order_id, api_key=self.api_key, agent_id=self.agent_id)
        raise AttributeError("CROO SDK does not implement get_order.")


_local_adapter = LocalCapAdapter()


def get_cap_adapter():
    """Returns either LocalCapAdapter or LiveCapAdapter depending on CAP_MODE."""
    mode = os.environ.get("CAP_MODE", "mock").lower()
    if mode == "live":
        sdk, api_key, agent_id = check_live_dependencies()
        return LiveCapAdapter(sdk, api_key, agent_id)
    return _local_adapter


