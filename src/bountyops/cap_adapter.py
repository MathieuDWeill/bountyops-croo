from __future__ import annotations

import dataclasses
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

    async def pay_order(self, order_id: str):
        return await self.client.pay_order(order_id)

    async def get_order(self, order_id: str):
        order = await self.client.get_order(order_id)
        try:
            parse_croo_order(order)
            return order
        except ValueError:
            # Fallback: list orders and match by ID
            for status in ["created", "paid"]:
                try:
                    orders = await self.list_orders(status=status)
                    for o in orders:
                        o_dict = to_dict(o)
                        o_id = o_dict.get("order_id") or o_dict.get("id")
                        if not o_id and hasattr(o, "order_id"):
                            o_id = getattr(o, "order_id")
                        elif not o_id and hasattr(o, "id"):
                            o_id = getattr(o, "id")
                        
                        if str(o_id) == str(order_id):
                            try:
                                parse_croo_order(o)
                                return o
                            except ValueError:
                                pass
                except Exception:
                    pass
                try:
                    options = self.sdk.ListOptions(role="provider", status=status)
                    orders = await self.client.list_orders(options)
                    for o in orders:
                        o_dict = to_dict(o)
                        o_id = o_dict.get("order_id") or o_dict.get("id")
                        if not o_id and hasattr(o, "order_id"):
                            o_id = getattr(o, "order_id")
                        elif not o_id and hasattr(o, "id"):
                            o_id = getattr(o, "id")
                        
                        if str(o_id) == str(order_id):
                            try:
                                parse_croo_order(o)
                                return o
                            except ValueError:
                                pass
                except Exception:
                    pass
            return order

    async def list_orders(self, status: str = "paid") -> list:
        options = self.sdk.ListOptions(role="provider", agent_id=self.agent_id, status=status)
        return await self.client.list_orders(options)

    async def deliver_order(self, order_id: str, result_payload: dict):
        serialized_result = safe_serialize(result_payload)
        
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
        req = self.sdk.DeliverOrderRequest(
            deliverable_type=self.sdk.DeliverableType.SCHEMA,
            deliverable_schema=schema_json,
            deliverable_text=""
        )
        return await self.client.deliver_order(order_id, req)

    async def list_negotiations(self, status: str = "pending") -> list:
        options = self.sdk.ListOptions(role="provider", status=status)
        return await self.client.list_negotiations(options)

    async def get_negotiation(self, negotiation_id: str):
        return await self.client.get_negotiation(negotiation_id)

    async def accept_negotiation(self, negotiation_id: str):
        return await self.client.accept_negotiation(negotiation_id)

    async def accept_negotiation_with_fund_address(self, negotiation_id: str, provider_fund_address: str):
        return await self.client.accept_negotiation_with_fund_address(negotiation_id, provider_fund_address)


_local_adapter = LocalCapAdapter()


def get_cap_adapter():
    """Returns either LocalCapAdapter or LiveCapAdapter depending on CAP_MODE."""
    mode = os.environ.get("CAP_MODE", "mock").lower()
    if mode == "live":
        sdk, api_key, agent_id = check_live_dependencies()
        return LiveCapAdapter(sdk, api_key, agent_id)
    return _local_adapter


def to_dict(obj):
    """Safely converts objects, dataclasses, models or dicts to a dict."""
    if obj is None:
        return {}
    val_type = type(obj)
    if val_type.__module__.startswith("unittest.mock") or val_type.__name__ in ("Mock", "MagicMock", "AsyncMock"):
        return {}
    
    d = {}
    if hasattr(obj, "__dict__"):
        d = vars(obj)
        if any(k in d for k in ["requirements", "payload", "request", "metadata"]):
            return d
            
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return obj.model_dump()
    if hasattr(obj, "dict") and callable(obj.dict):
        return obj.dict()
        
    if d:
        return d
        
    if isinstance(obj, dict):
        return obj
    try:
        return dict(obj)
    except (TypeError, ValueError):
        pass
    return {}


def parse_croo_order(order) -> RunRequest:
    """Extracts order requirements from possible SDK order shapes and converts to RunRequest."""
    raw_req = None

    order_dict = to_dict(order)
    if order_dict:
        raw_req = order_dict.get("requirements") or order_dict.get("payload") or order_dict.get("request") or order_dict.get("metadata")

    if not raw_req:
        def get_valid_val(obj, name):
            if not hasattr(obj, name):
                return None
            val = getattr(obj, name)
            val_type = type(val)
            if val_type.__module__.startswith("unittest.mock") or val_type.__name__ in ("Mock", "MagicMock", "AsyncMock"):
                return None
            return val

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


def sanitize_sdk_order(order):
    """Converts a raw SDK order object to a sanitized dict, removing secret fields."""
    def serialize_and_sanitize(val):
        if val is None:
            return None
        val_type = type(val)
        if val_type.__module__.startswith("unittest.mock") or val_type.__name__ in ("Mock", "MagicMock", "AsyncMock"):
            return None
        
        if isinstance(val, dict):
            res = {}
            for k, v in val.items():
                kl = k.lower()
                is_container = not isinstance(v, (str, bytes, bool, int, float)) and (
                    isinstance(v, (dict, list)) or hasattr(v, "__dict__") or (hasattr(v, "keys") and hasattr(v, "__getitem__"))
                )
                if not is_container and any(secret in kl for secret in ["key", "secret", "token", "password", "auth", "credential"]):
                    continue
                res[k] = serialize_and_sanitize(v)
            return res
        elif isinstance(val, list):
            return [serialize_and_sanitize(item) for item in val]
        elif hasattr(val, "model_dump") and callable(val.model_dump):
            return serialize_and_sanitize(val.model_dump())
        elif hasattr(val, "dict") and callable(val.dict):
            return serialize_and_sanitize(val.dict())
        elif hasattr(val, "__dict__"):
            return serialize_and_sanitize(vars(val))
        elif hasattr(val, "keys") and hasattr(val, "__getitem__"):
            try:
                return serialize_and_sanitize(dict(val))
            except Exception:
                pass
        
        # If it is a string that is valid JSON, try to parse it
        if isinstance(val, str):
            val_stripped = val.strip()
            if (val_stripped.startswith("{") and val_stripped.endswith("}")) or (val_stripped.startswith("[") and val_stripped.endswith("]")):
                try:
                    parsed = json.loads(val)
                    return serialize_and_sanitize(parsed)
                except Exception:
                    pass
        return val

    return serialize_and_sanitize(order)


def safe_serialize(obj):
    """Safely serializes any object to JSON-compatible primitives."""
    if obj is None:
        return None
    val_type = type(obj)
    if val_type.__module__.startswith("unittest.mock") or val_type.__name__ in ("Mock", "MagicMock", "AsyncMock"):
        return None
        
    if dataclasses.is_dataclass(obj):
        return safe_serialize(dataclasses.asdict(obj))
    elif hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return safe_serialize(obj.model_dump(mode="json"))
        except TypeError:
            return safe_serialize(obj.model_dump())
    elif hasattr(obj, "dict") and callable(obj.dict):
        return safe_serialize(obj.dict())
    elif isinstance(obj, dict):
        return {str(k): safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_serialize(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif hasattr(obj, "__dict__"):
        attrs = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        return safe_serialize(attrs)
    else:
        return str(obj)


async def resolve_live_order_requirements(adapter, order_id: str, order=None):
    """Resolves the RunRequest for an order.
    
    1. First tries to parse the requirements directly from the order.
    2. If that fails and order has negotiation_id, resolves from the linked negotiation:
       - first try get_negotiation(negotiation_id)
       - if unavailable/fails, list accepted negotiations and match by negotiation_id.
    3. If negotiation fallback is not applicable or fails, list provider orders and match by order_id.
    """
    if order is None:
        order = await adapter.client.get_order(order_id)
    
    order_err = None
    try:
        req = parse_croo_order(order)
        return req, "order", None
    except ValueError as e:
        order_err = str(e)
        
    order_dict = to_dict(order)
    negotiation_id = order_dict.get("negotiation_id")
    if not negotiation_id and hasattr(order, "negotiation_id"):
        negotiation_id = getattr(order, "negotiation_id")
        
    if negotiation_id:
        negotiation = None
        try:
            negotiation = await adapter.get_negotiation(negotiation_id)
            if negotiation:
                req = parse_croo_order(negotiation)
                return req, "negotiation", negotiation
        except Exception:
            pass
            
        try:
            negs = await adapter.list_negotiations(status="accepted")
            for neg in negs:
                neg_dict = to_dict(neg)
                neg_id = neg_dict.get("negotiation_id") or neg_dict.get("id")
                if not neg_id and hasattr(neg, "negotiation_id"):
                    neg_id = getattr(neg, "negotiation_id")
                elif not neg_id and hasattr(neg, "id"):
                    neg_id = getattr(neg, "id")
                    
                if str(neg_id) == str(negotiation_id):
                    req = parse_croo_order(neg)
                    return req, "negotiation", neg
        except Exception:
            pass

    for status in ["created", "paid"]:
        try:
            orders = await adapter.list_orders(status=status)
            for o in orders:
                o_dict = to_dict(o)
                o_id = o_dict.get("order_id") or o_dict.get("id")
                if not o_id and hasattr(o, "order_id"):
                    o_id = getattr(o, "order_id")
                elif not o_id and hasattr(o, "id"):
                    o_id = getattr(o, "id")
                
                if str(o_id) == str(order_id):
                    try:
                        req = parse_croo_order(o)
                        return req, "order", None
                    except ValueError:
                        pass
        except Exception:
            pass
        
        try:
            options = adapter.sdk.ListOptions(role="provider", status=status)
            orders = await adapter.client.list_orders(options)
            for o in orders:
                o_dict = to_dict(o)
                o_id = o_dict.get("order_id") or o_dict.get("id")
                if not o_id and hasattr(o, "order_id"):
                    o_id = getattr(o, "order_id")
                elif not o_id and hasattr(o, "id"):
                    o_id = getattr(o, "id")
                
                if str(o_id) == str(order_id):
                    try:
                        req = parse_croo_order(o)
                        return req, "order", None
                    except ValueError:
                        pass
        except Exception:
            pass

    raise ValueError(f"Could not resolve requirements for order {order_id} (Order parsing error: {order_err})")
