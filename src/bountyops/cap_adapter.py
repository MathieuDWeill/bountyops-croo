from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta

from .models import (
    BuilderProfile,
    LedgerEvent,
    Opportunity,
    Order,
    OrderStatus,
    Quote,
    QuoteRequest,
    RunRequest,
)
from .orchestrator import run_bountyops



class LocalCapAdapter:
    """Small local adapter that mirrors the lifecycle of a paid CAP-callable agent.

    This is intentionally simple so reviewers can run it without chain credentials.
    Replace this class with live CROO SDK calls when using a production Agent Store listing.
    """

    def __init__(self):
        self.orders: dict[str, Order] = {}

    async def capabilities(self) -> dict:
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

    async def quote(self, request: QuoteRequest) -> Quote:
        return Quote(
            price_usdc=25.0,
            expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            deliverables=["submission_pack", "specialist_order_ledger", "proof_hash"],
        )

    async def create_order(self, request: RunRequest) -> Order:
        quote = await self.quote(QuoteRequest(**request.model_dump()))
        order = Order(quote=quote, request=request)
        order.ledger.append(LedgerEvent(actor="Buyer", action="order_created", counterparty="BountyOps"))
        self.orders[order.order_id] = order
        return order

    async def pay_order(self, order_id: str) -> Order:
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

    async def get_order(self, order_id: str) -> Order:
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
    
    sdk_key = os.environ.get("CROO_SDK_KEY")
    api_url = os.environ.get("CROO_API_URL")
    ws_url = os.environ.get("CROO_WS_URL")
    agent_id = os.environ.get("CROO_AGENT_ID")
    
    missing = []
    if not sdk_key:
        missing.append("CROO_SDK_KEY")
    if not api_url:
        missing.append("CROO_API_URL")
    if not ws_url:
        missing.append("CROO_WS_URL")
    if not agent_id:
        missing.append("CROO_AGENT_ID")
        
    if missing:
        raise ValueError(f"CROO credentials missing: {', '.join(missing)}")
        
    return sdk, sdk_key, agent_id


class LiveCapAdapter:
    """Live CAP Adapter that delegates to the live CROO SDK."""

    def __init__(self, sdk, api_key: str, agent_id: str):
        self.sdk = sdk
        self.api_key = api_key
        self.agent_id = agent_id

        config = sdk.Config(
            base_url=os.environ.get("CROO_API_URL", "https://api.croo.network"),
            ws_url=os.environ.get("CROO_WS_URL", "wss://api.croo.network/ws"),
            rpc_url=os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
        )
        self.client = sdk.AgentClient(config, api_key)

    async def capabilities(self) -> dict:
        if self.client and hasattr(self.client, "capabilities"):
            res = self.client.capabilities()
            import inspect
            if inspect.isawaitable(res):
                return await res
            return res
        return {
            "agent": "BountyOps",
            "agent_id": self.agent_id,
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

    async def quote(self, request: QuoteRequest) -> Quote:
        return Quote(
            price_usdc=25.0,
            expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            deliverables=["submission_pack", "specialist_order_ledger", "proof_hash"],
        )

    async def create_order(self, request: RunRequest) -> Order:
        raise NotImplementedError("In live mode, order creation is handled by the CROO network/buyer agent.")

    async def pay_order(self, order_id: str) -> Order:
        raise NotImplementedError("In live mode, payments and order execution events are handled via the CROO network/worker.")

    async def get_order(self, order_id: str):
        return await self.client.get_order(order_id)

    async def list_orders(self, status: str = "paid") -> list:
        options = self.sdk.ListOptions(role="provider", agent_id=self.agent_id, status=status)
        return await self.client.list_orders(options)

    async def deliver_order(self, order_id: str, result_payload: dict):
        req = {
            "type": self.sdk.DeliverableType.SCHEMA,
            "value": result_payload
        }
        return await self.client.deliver_order(order_id, req)

    async def list_negotiations(self, status: str = "pending") -> list:
        options = self.sdk.ListOptions(role="provider", status=status)
        return await self.client.list_negotiations(options)

    async def get_negotiation(self, negotiation_id: str):
        return await self.client.get_negotiation(negotiation_id)

    async def accept_negotiation(self, negotiation_id: str):
        return await self.client.accept_negotiation(negotiation_id)



_local_adapter = LocalCapAdapter()


def get_cap_adapter():
    """Returns either LocalCapAdapter or LiveCapAdapter depending on CAP_MODE."""
    mode = os.environ.get("CAP_MODE", "mock").lower()
    if mode == "live":
        sdk, api_key, agent_id = check_live_dependencies()
        return LiveCapAdapter(sdk, api_key, agent_id)
    return _local_adapter

def parse_croo_order(order) -> RunRequest:
    """Extracts order requirements from possible SDK order shapes and converts to RunRequest."""
    raw_req = None

    def get_valid_val(obj, name):
        if not hasattr(obj, name):
            return None
        val = getattr(obj, name)
        # Filter out Mock objects to avoid false-positives in unit tests
        val_type = type(val)
        if val_type.__module__.startswith("unittest.mock") or val_type.__name__ in ("Mock", "MagicMock", "AsyncMock"):
            return None
        return val

    if isinstance(order, dict):
        raw_req = order.get("requirements") or order.get("payload") or order.get("request") or order.get("metadata")
    else:
        raw_req = (
            get_valid_val(order, "requirements")
            or get_valid_val(order, "payload")
            or get_valid_val(order, "request")
            or get_valid_val(order, "metadata")
        )

    if not raw_req:
        raise ValueError("Order lacks a compatible payload or requirements field.")

    # 2. If it is a JSON string, load it
    if isinstance(raw_req, str):
        try:
            raw_req = json.loads(raw_req)
        except Exception:
            pass # Keep it as string if it is not valid JSON

    # 3. Check if it's already a nested RunRequest/dict with builder_profile
    if isinstance(raw_req, dict) and "builder_profile" in raw_req and "opportunity" in raw_req:
        return RunRequest(**raw_req)

    # 4. Handle flat CROO schema
    if isinstance(raw_req, dict):
        opportunity_title = raw_req.get("opportunity_title")
        opportunity_description = raw_req.get("opportunity_description")
        prize_pool_usd = raw_req.get("prize_pool_usd")
        deadline = raw_req.get("deadline")
        builder_profile_str = raw_req.get("builder_profile")

        if opportunity_title or builder_profile_str:
            builder_name = "CROO Buyer"
            skills = []
            time_budget_days = 3
            goal = "maximize expected value"

            if builder_profile_str and isinstance(builder_profile_str, str):
                if "." in builder_profile_str:
                    first_part = builder_profile_str.split(".")[0].strip()
                    if first_part and "skills" not in first_part.lower():
                        builder_name = first_part

                skills_match = re.search(r"skills:\s*([^.]+)", builder_profile_str, re.IGNORECASE)
                if skills_match:
                    skills_text = skills_match.group(1)
                    skills = [s.strip() for s in re.split(r"[,;]", skills_text) if s.strip()]

                hours_match = re.search(r"(\d+)\s*hours", builder_profile_str, re.IGNORECASE)
                available_hours = 20
                if hours_match:
                    available_hours = int(hours_match.group(1))
                time_budget_days = max(1, available_hours // 8)

                goal_match = re.search(r"goal:\s*([^.]+)", builder_profile_str, re.IGNORECASE)
                if goal_match:
                    goal = goal_match.group(1).strip()

            req_list = []
            if opportunity_description:
                req_list = [opportunity_description]

            prize = 0.0
            if prize_pool_usd is not None:
                try:
                    prize = float(prize_pool_usd)
                except ValueError:
                    pass

            profile = BuilderProfile(
                name=builder_name,
                skills=skills,
                time_budget_days=time_budget_days,
                goal=goal
            )

            opportunity = Opportunity(
                title=opportunity_title or "Unknown Opportunity",
                prize_pool_usd=prize,
                deadline=str(deadline) if deadline else None,
                requirements=req_list
            )

            return RunRequest(
                builder_profile=profile,
                opportunity=opportunity
            )

    raise ValueError("Order payload shape is not recognized.")
