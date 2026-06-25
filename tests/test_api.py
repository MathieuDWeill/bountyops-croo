from dataclasses import dataclass
import json
import os
from pathlib import Path
import pytest


@dataclass
class DeliverOrderRequest:
    deliverable_type: str
    deliverable_schema: str = ""
    deliverable_text: str = ""


@dataclass
class Order:
    order_id: str = ""
    status: str = ""


@dataclass
class PayOrderResult:
    order: Order
    tx_hash: str = ""

from fastapi.testclient import TestClient

from bountyops.app import app

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.setenv("CAP_MODE", "mock")
    for var in [
        "CROO_API_URL",
        "CROO_WS_URL",
        "CROO_AGENT_ID",
        "CROO_API_KEY",
        "CROO_SDK_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_order_lifecycle():
    payload = json.loads(Path("examples/croo_input.json").read_text())
    created = client.post("/orders", json=payload)
    assert created.status_code == 200
    order_id = created.json()["order_id"]

    paid = client.post(f"/orders/{order_id}/pay")
    assert paid.status_code == 200
    body = paid.json()
    assert body["status"] == "completed"
    assert body["result"]["proof_hash"].startswith("sha256:")


def test_cap_mode_default():
    response = client.get("/cap/mode")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "mock"
    assert isinstance(data["sdk_available"], bool)
    assert data["credentials_available"] is False


def test_cap_live_capabilities_fails_clearly():
    response = client.get("/cap/live/capabilities")
    assert response.status_code == 500
    assert "missing" in response.json()["detail"].lower()


def test_live_mode_missing_dependencies_fails_clearly(monkeypatch):
    monkeypatch.setenv("CAP_MODE", "live")
    response = client.get("/capabilities")
    assert response.status_code == 500
    assert "missing" in response.json()["detail"].lower()


def test_live_mode_success_with_mock_sdk(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    mock_client.capabilities = AsyncMock(return_value={"agent": "BountyOpsLive", "wallet": "0xLiveWallet"})
    mock_client.quote = AsyncMock(return_value={
        "quote_id": "quote_live",
        "service": "opportunity_to_submission_pack",
        "price_usdc": 25.0,
        "estimated_specialist_orders": 5,
        "expires_at": "2026-06-24T12:00:00Z",
        "deliverables": ["live_pack"]
    })

    mock_croo.Config = MagicMock()
    mock_croo.ListOptions = MagicMock()
    mock_croo.DeliverableType = MagicMock()
    mock_croo.EventType = MagicMock()

    # Inject mock SDK
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")

    # Verify /cap/mode shows live and available
    response = client.get("/cap/mode")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "live"
    assert data["sdk_available"] is True
    assert data["credentials_available"] is True

    # Verify /cap/live/capabilities returns our mock
    response = client.get("/cap/live/capabilities")
    assert response.status_code == 200
    assert response.json()["agent"] == "BountyOpsLive"

    # Verify general /capabilities returns our mock
    response = client.get("/capabilities")
    assert response.status_code == 200
    assert response.json()["agent"] == "BountyOpsLive"


def test_cap_live_orders_endpoint(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    mock_orders = [{"order_id": "order_123", "payload": {"opportunity": {"title": "Test Opp", "platform": "Platform"}}}]
    mock_client.list_orders = AsyncMock(return_value=mock_orders)
    
    mock_croo.Config = MagicMock()
    mock_croo.ListOptions = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.get("/cap/live/orders?status=paid")
    assert response.status_code == 200
    assert response.json() == mock_orders
    mock_client.list_orders.assert_called_once()


def test_cap_live_deliver_endpoint(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_croo.DeliverOrderRequest = DeliverOrderRequest
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    mock_order = MagicMock()
    mock_order.payload = {
        "builder_profile": {
            "name": "Test Builder",
            "skills": ["python"],
            "time_budget_days": 3,
            "goal": "maximize expected value"
        },
        "opportunity": {
            "title": "Test Opportunity",
            "prize_pool_usd": 1000
        }
    }
    mock_client.get_order = AsyncMock(return_value=mock_order)
    mock_client.deliver_order = AsyncMock()
    
    mock_croo.Config = MagicMock()
    mock_croo.DeliverableType = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.post("/cap/live/deliver/order_123")
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"
    assert response.json()["order_id"] == "order_123"
    assert response.json()["proof_hash"].startswith("sha256:")
    mock_client.get_order.assert_called_once_with("order_123")
    mock_client.deliver_order.assert_called_once()


def test_cap_live_run_paid_orders_endpoint(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_croo.DeliverOrderRequest = DeliverOrderRequest
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    mock_order = {
        "id": "order_456",
        "payload": {
            "builder_profile": {
                "name": "Test Builder",
                "skills": ["python"],
                "time_budget_days": 3,
                "goal": "maximize expected value"
            },
            "opportunity": {
                "title": "Test Opportunity",
                "prize_pool_usd": 1000
            }
        }
    }
    mock_client.list_orders = AsyncMock(return_value=[mock_order])
    mock_client.deliver_order = AsyncMock()
    
    mock_croo.Config = MagicMock()
    mock_croo.ListOptions = MagicMock()
    mock_croo.DeliverableType = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.post("/cap/live/run-paid-orders")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["processed_order_ids"] == ["order_456"]
    mock_client.deliver_order.assert_called_once()



def test_cap_live_list_negotiations(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    mock_negotiations = [{"negotiation_id": "neg_123", "status": "pending"}]
    mock_client.list_negotiations = AsyncMock(return_value=mock_negotiations)
    
    mock_croo.Config = MagicMock()
    mock_croo.ListOptions = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.get("/cap/live/negotiations?status=pending")
    assert response.status_code == 200
    assert response.json() == mock_negotiations
    mock_client.list_negotiations.assert_called_once()


def test_cap_live_accept_negotiation(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    mock_client.accept_negotiation = AsyncMock()
    
    mock_croo.Config = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.post("/cap/live/negotiations/neg_123/accept")
    assert response.status_code == 200
    assert response.json() == {"status": "accepted", "negotiation_id": "neg_123"}
    mock_client.accept_negotiation.assert_called_once_with("neg_123")

def test_cap_live_deliver_flat_requirements(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_croo.DeliverOrderRequest = DeliverOrderRequest
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    # Mock order response containing requirements as a JSON string
    mock_order = MagicMock()
    mock_order.requirements = json.dumps({
        "deadline": "2026-07-12",
        "prize_pool_usd": 10200,
        "builder_profile": "Mathieu Weill. Skills: Python, FastAPI, AI agents, product strategy, hackathon shipping. Available time: around 20 hours. Goal: build a serious, production-grade agent product with real CROO runtime integration, not a mock.",
        "opportunity_title": "CROO Agent Hackathon",
        "opportunity_description": "Build and submit a CROO-compatible autonomous agent. The agent must be listed on the CROO Agent Store, integrate with CAP, expose a callable service, return a verifiable deliverable, include an open-source GitHub repository, and provide a short demo video and DoraHacks submission."
    })
    
    mock_client.get_order = AsyncMock(return_value=mock_order)
    mock_client.deliver_order = AsyncMock()
    
    mock_croo.Config = MagicMock()
    mock_croo.DeliverableType = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.post("/cap/live/deliver/order_789")
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"
    assert response.json()["order_id"] == "order_789"
    assert response.json()["proof_hash"].startswith("sha256:")
    mock_client.get_order.assert_called_once_with("order_789")
    mock_client.deliver_order.assert_called_once()


def test_parse_croo_order_shapes():
    from bountyops.cap_adapter import parse_croo_order
    from bountyops.models import RunRequest

    # 1. SDK object with requirements attribute
    class SDKOrderObject:
        def __init__(self, requirements):
            self.requirements = requirements
            self.order_id = "order_1"

    req_val = {
        "opportunity_title": "SDK Title",
        "opportunity_description": "SDK Description",
        "prize_pool_usd": 5000,
        "deadline": "2026-08-01",
        "builder_profile": "Name. Skills: Py. Goal: win"
    }
    sdk_obj = SDKOrderObject(requirements=json.dumps(req_val))
    res1 = parse_croo_order(sdk_obj)
    assert isinstance(res1, RunRequest)
    assert res1.opportunity.title == "SDK Title"

    # 2. dict order with requirements
    dict_order = {
        "requirements": req_val
    }
    res2 = parse_croo_order(dict_order)
    assert isinstance(res2, RunRequest)
    assert res2.opportunity.title == "SDK Title"

    # 3. Pydantic-like object with model_dump or dict
    class PydanticOrder:
        def __init__(self, requirements):
            self._req = requirements
        def model_dump(self):
            return {"requirements": self._req}

    pydantic_obj = PydanticOrder(requirements=req_val)
    res3 = parse_croo_order(pydantic_obj)
    assert isinstance(res3, RunRequest)
    assert res3.opportunity.title == "SDK Title"


def test_cap_live_deliver_fallback(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_croo.DeliverOrderRequest = DeliverOrderRequest
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    # get_order returns order missing requirements
    bad_order = MagicMock()
    bad_order.requirements = None
    bad_order.payload = None
    bad_order.order_id = "fallback_123"
    
    # list_orders returns the matching order WITH requirements
    good_order = MagicMock()
    good_order.order_id = "fallback_123"
    good_order.requirements = json.dumps({
        "deadline": "2026-07-12",
        "prize_pool_usd": 10200,
        "builder_profile": "Mathieu Weill. Skills: Python, FastAPI. Goal: build a serious agent",
        "opportunity_title": "CROO Agent Hackathon",
        "opportunity_description": "Build and submit a CROO-compatible autonomous agent."
    })
    
    mock_client.get_order = AsyncMock(return_value=bad_order)
    mock_client.list_orders = AsyncMock(return_value=[good_order])
    mock_client.deliver_order = AsyncMock()
    
    mock_croo.Config = MagicMock()
    mock_croo.DeliverableType = MagicMock()
    mock_croo.ListOptions = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.post("/cap/live/deliver/fallback_123")
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"
    assert response.json()["order_id"] == "fallback_123"
    assert response.json()["proof_hash"].startswith("sha256:")
    
    mock_client.get_order.assert_called_once_with("fallback_123")
    mock_client.list_orders.assert_called()
    mock_client.deliver_order.assert_called_once()


def test_cap_live_order_debug_endpoint(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    # Order contains public fields and some secret keys/tokens
    raw_order = {
        "id": "order_debug_123",
        "status": "paid",
        "requirements": '{"opportunity_title": "Debug Opportunity"}',
        "api_key": "secret-api-key-that-must-be-hidden",
        "some_token": "token-123",
        "nested_secrets": {
            "secret_word": "password123",
            "public_field": "visible"
        }
    }
    
    mock_client.get_order = AsyncMock(return_value=raw_order)
    mock_croo.Config = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.get("/cap/live/orders/order_debug_123/debug")
    assert response.status_code == 200
    res_json = response.json()
    
    # Check the new debug endpoint output shape
    assert "raw_order" in res_json
    assert res_json["parse_source"] == "order"
    assert res_json["parser_error"] is None
    
    raw_order_res = res_json["raw_order"]
    assert "api_key" not in raw_order_res
    assert "some_token" not in raw_order_res
    assert "secret_word" not in raw_order_res["nested_secrets"]
    assert raw_order_res["id"] == "order_debug_123"
    assert raw_order_res["status"] == "paid"
    assert raw_order_res["requirements"]["opportunity_title"] == "Debug Opportunity"
    assert raw_order_res["nested_secrets"]["public_field"] == "visible"
    
    mock_client.get_order.assert_called_once_with("order_debug_123")


def test_cap_live_deliver_via_negotiation_direct(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_croo.DeliverOrderRequest = DeliverOrderRequest
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    class DummyOrder:
        def __init__(self, order_id, negotiation_id):
            self.order_id = order_id
            self.negotiation_id = negotiation_id
            self.requirements = None
            self.payload = None

    class DummyNegotiation:
        def __init__(self, negotiation_id, requirements):
            self.negotiation_id = negotiation_id
            self.requirements = requirements

    bad_order = DummyOrder(order_id="order_neg_1", negotiation_id="neg_direct_123")
    
    mock_negotiation = DummyNegotiation(
        negotiation_id="neg_direct_123",
        requirements=json.dumps({
            "opportunity_title": "Negotiated Opportunity Direct",
            "opportunity_description": "Submitting draft",
            "prize_pool_usd": 8500,
            "deadline": "2026-10-10",
            "builder_profile": "Mathieu. Skills: Python, FastAPI. Goal: build live"
        })
    )
    
    mock_client.get_order = AsyncMock(return_value=bad_order)
    mock_client.get_negotiation = AsyncMock(return_value=mock_negotiation)
    mock_client.deliver_order = AsyncMock()
    
    mock_croo.Config = MagicMock()
    mock_croo.DeliverableType = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.post("/cap/live/deliver/order_neg_1")
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"
    assert response.json()["order_id"] == "order_neg_1"
    assert response.json()["proof_hash"].startswith("sha256:")
    
    mock_client.get_order.assert_called_once_with("order_neg_1")
    mock_client.get_negotiation.assert_called_once_with("neg_direct_123")
    mock_client.deliver_order.assert_called_once()
    
    # Also verify debug endpoint trace
    debug_response = client.get("/cap/live/orders/order_neg_1/debug")
    assert debug_response.status_code == 200
    debug_json = debug_response.json()
    assert debug_json["parse_source"] == "negotiation"
    assert debug_json["linked_negotiation"]["requirements"]["opportunity_title"] == "Negotiated Opportunity Direct"


def test_cap_live_deliver_via_negotiation_fallback_list(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_croo.DeliverOrderRequest = DeliverOrderRequest
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    class DummyOrder:
        def __init__(self, order_id, negotiation_id):
            self.order_id = order_id
            self.negotiation_id = negotiation_id
            self.requirements = None
            self.payload = None

    class DummyNegotiation:
        def __init__(self, negotiation_id, requirements):
            self.negotiation_id = negotiation_id
            self.requirements = requirements

    bad_order = DummyOrder(order_id="order_neg_2", negotiation_id="neg_list_456")
    
    # get_negotiation raises exception/fails/unavailable
    mock_client.get_order = AsyncMock(return_value=bad_order)
    mock_client.get_negotiation = AsyncMock(side_effect=Exception("Method not found or RPC error"))
    
    matching_negotiation = DummyNegotiation(
        negotiation_id="neg_list_456",
        requirements=json.dumps({
            "opportunity_title": "Negotiated Opportunity Fallback List",
            "opportunity_description": "DoraHacks demo link required",
            "prize_pool_usd": 12000,
            "deadline": "2026-11-11",
            "builder_profile": "Mathieu. Skills: Python, Docker. Goal: ship"
        })
    )
    
    mock_client.list_negotiations = AsyncMock(return_value=[matching_negotiation])
    mock_client.deliver_order = AsyncMock()
    
    mock_croo.Config = MagicMock()
    mock_croo.DeliverableType = MagicMock()
    mock_croo.ListOptions = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    response = client.post("/cap/live/deliver/order_neg_2")
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"
    assert response.json()["order_id"] == "order_neg_2"
    
    mock_client.get_order.assert_called_once_with("order_neg_2")
    mock_client.get_negotiation.assert_called_once_with("neg_list_456")
    mock_client.list_negotiations.assert_called_once()
    mock_client.deliver_order.assert_called_once()


def test_safe_serialize():
    from bountyops.cap_adapter import safe_serialize
    from dataclasses import dataclass

    # 1. Primitive
    assert safe_serialize(123) == 123
    assert safe_serialize("test") == "test"
    assert safe_serialize(True) is True
    assert safe_serialize(None) is None

    # 2. Dataclass
    @dataclass
    class SimpleDataclass:
        a: int
        b: str

    obj = SimpleDataclass(a=1, b="two")
    assert safe_serialize(obj) == {"a": 1, "b": "two"}

    # 3. Pydantic-like object
    class PydanticLike:
        def model_dump(self, mode=None):
            return {"c": 3, "d": [4, 5]}

    assert safe_serialize(PydanticLike()) == {"c": 3, "d": [4, 5]}

    # 4. Standard Dict/List
    mixed = {"list": [SimpleDataclass(a=9, b="nine")], "val": PydanticLike()}
    assert safe_serialize(mixed) == {
        "list": [{"a": 9, "b": "nine"}],
        "val": {"c": 3, "d": [4, 5]}
    }

    # 5. Normal class object
    class NormalClass:
        def __init__(self):
            self.x = 10
            self._private = 20

    assert safe_serialize(NormalClass()) == {"x": 10}


@pytest.mark.anyio
async def test_cap_live_deliver_pydantic_serialization(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    mock_croo.DeliverOrderRequest = DeliverOrderRequest
    mock_croo.DeliverableType.SCHEMA = "schema"
    
    class MockRunResult:
        def __init__(self):
            self.proof_hash = "sha256:12345"
            self.submission_pack = {
                "go_no_go": "GO",
                "expected_value_score": 8,
                "recommended_project": "AI Agent"
            }
            
        def model_dump(self, mode=None):
            return {
                "proof_hash": self.proof_hash,
                "submission_pack": self.submission_pack
            }
            
    mock_order = MagicMock()
    mock_order.requirements = '{"opportunity_title": "Test"}'
    mock_client.get_order = AsyncMock(return_value=mock_order)
    
    captured_reqs = []
    async def capture_deliver(order_id, req):
        captured_reqs.append(req)
        mock_result = MagicMock()
        return mock_result
        
    mock_client.deliver_order = AsyncMock(side_effect=capture_deliver)
    
    mock_croo.Config = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    from bountyops.cap_adapter import get_cap_adapter
    adapter = get_cap_adapter()
    
    run_result = MockRunResult()
    
    await adapter.deliver_order("order_123", run_result)
    
    assert len(captured_reqs) == 1
    req = captured_reqs[0]
    assert isinstance(req, DeliverOrderRequest)
    assert req.deliverable_type == "schema"
    
    parsed_schema = json.loads(req.deliverable_schema)
    assert parsed_schema["proof_hash"] == "sha256:12345"
    assert parsed_schema["go_no_go"] == "GO"
    assert parsed_schema["expected_value_score"] == 8.0
    assert parsed_schema["recommended_project"] == "AI Agent"
    
    assert isinstance(parsed_schema["submission_pack"], str)
    full_payload = json.loads(parsed_schema["submission_pack"])
    assert full_payload["proof_hash"] == "sha256:12345"
    assert full_payload["submission_pack"]["go_no_go"] == "GO"


def test_cap_live_pay_order_endpoint(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    # Setup PayOrderResult mock response
    pay_res = PayOrderResult(
        order=Order(order_id="pay_123", status="paid"),
        tx_hash="0xTxHash123"
    )
    mock_client.pay_order = AsyncMock(return_value=pay_res)
    mock_croo.Config = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")
    
    # Test successful payment
    response = client.post("/cap/live/orders/pay_123/pay")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["order"]["order_id"] == "pay_123"
    assert res_json["order"]["status"] == "paid"
    assert res_json["tx_hash"] == "0xTxHash123"
    mock_client.pay_order.assert_called_once_with("pay_123")
    
    # Test error propagation
    mock_client.pay_order = AsyncMock(side_effect=ValueError("INVALID_STATUS: order can only be paid when status is created"))
    err_response = client.post("/cap/live/orders/pay_123/pay")
    assert err_response.status_code == 500
    assert "INVALID_STATUS" in err_response.json()["detail"]


def test_cap_live_accept_direct_endpoint(monkeypatch):
    import sys
    from unittest.mock import MagicMock, AsyncMock

    mock_croo = MagicMock()
    mock_client = MagicMock()
    mock_croo.AgentClient.return_value = mock_client
    
    mock_client.accept_negotiation_with_fund_address = AsyncMock(return_value={"status": "ok"})
    mock_croo.Config = MagicMock()
    
    monkeypatch.setitem(sys.modules, "croo", mock_croo)
    monkeypatch.setenv("CAP_MODE", "live")
    monkeypatch.setenv("CROO_SDK_KEY", "test-key")
    monkeypatch.setenv("CROO_API_URL", "test-api")
    monkeypatch.setenv("CROO_WS_URL", "test-ws")
    monkeypatch.setenv("CROO_AGENT_ID", "test-agent")

    # 1. Test success with body
    response = client.post(
        "/cap/live/negotiations/neg_abc/accept-direct",
        json={"provider_fund_address": "0xBodyAddress"}
    )
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "accepted_direct"
    assert res_json["negotiation_id"] == "neg_abc"
    assert res_json["provider_fund_address"] == "0xBodyAddress"
    mock_client.accept_negotiation_with_fund_address.assert_called_once_with("neg_abc", "0xBodyAddress")

    # Reset mock
    mock_client.accept_negotiation_with_fund_address.reset_mock()

    # 2. Test success with environment variable (and no body)
    monkeypatch.setenv("CROO_PROVIDER_FUND_ADDRESS", "0xEnvAddress")
    response = client.post("/cap/live/negotiations/neg_abc/accept-direct")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "accepted_direct"
    assert res_json["provider_fund_address"] == "0xEnvAddress"
    mock_client.accept_negotiation_with_fund_address.assert_called_once_with("neg_abc", "0xEnvAddress")

    # Reset mock and environment variable
    mock_client.accept_negotiation_with_fund_address.reset_mock()
    monkeypatch.delenv("CROO_PROVIDER_FUND_ADDRESS", raising=False)

    # 3. Test failure when address is missing
    response = client.post("/cap/live/negotiations/neg_abc/accept-direct")
    assert response.status_code == 400
    assert "provider_fund_address is required" in response.json()["detail"]


@pytest.mark.anyio
async def test_worker_handle_negotiation_created(monkeypatch):
    from unittest.mock import MagicMock, AsyncMock
    from scripts.croo_provider_worker import handle_negotiation_created

    mock_client = MagicMock()
    
    # Mock return values for get_negotiation
    normal_neg = {"negotiation_id": "neg_normal", "fund_amount": None, "fund_token": None}
    direct_neg_amount = {"negotiation_id": "neg_direct_amt", "fund_amount": 100, "fund_token": None}
    direct_neg_token = {"negotiation_id": "neg_direct_tok", "fund_amount": None, "fund_token": "USDC"}
    
    mock_client.get_negotiation = AsyncMock(side_effect=lambda nid: {
        "neg_normal": normal_neg,
        "neg_direct_amt": direct_neg_amount,
        "neg_direct_tok": direct_neg_token
    }.get(nid, normal_neg))
    
    mock_client.accept_negotiation = AsyncMock()
    mock_client.accept_negotiation_with_fund_address = AsyncMock()

    # 1. Test normal mode (no direct flag, no env)
    await handle_negotiation_created({"id": "neg_normal"}, mock_client)
    mock_client.accept_negotiation.assert_called_once_with("neg_normal")
    mock_client.accept_negotiation_with_fund_address.assert_not_called()

    # Reset mocks
    mock_client.accept_negotiation.reset_mock()
    mock_client.accept_negotiation_with_fund_address.reset_mock()

    # 2. Test direct negotiation without CROO_DIRECT_ACCEPT=true uses standard accept
    await handle_negotiation_created({"id": "neg_direct_amt"}, mock_client)
    mock_client.accept_negotiation.assert_called_once_with("neg_direct_amt")
    mock_client.accept_negotiation_with_fund_address.assert_not_called()

    # Reset mocks
    mock_client.accept_negotiation.reset_mock()
    mock_client.accept_negotiation_with_fund_address.reset_mock()

    # 3. Test direct mode due to CROO_DIRECT_ACCEPT=true (with normal negotiation)
    monkeypatch.setenv("CROO_DIRECT_ACCEPT", "true")
    monkeypatch.setenv("CROO_PROVIDER_FUND_ADDRESS", "0xFundAddress")
    await handle_negotiation_created({"id": "neg_normal"}, mock_client)
    mock_client.accept_negotiation.assert_not_called()
    mock_client.accept_negotiation_with_fund_address.assert_called_once_with("neg_normal", "0xFundAddress")

    # Reset mocks & env
    mock_client.accept_negotiation.reset_mock()
    mock_client.accept_negotiation_with_fund_address.reset_mock()
    monkeypatch.delenv("CROO_DIRECT_ACCEPT", raising=False)
    monkeypatch.delenv("CROO_PROVIDER_FUND_ADDRESS", raising=False)

    # 4. Test direct mode error when CROO_PROVIDER_FUND_ADDRESS is missing
    monkeypatch.setenv("CROO_DIRECT_ACCEPT", "true")
    await handle_negotiation_created({"id": "neg_normal"}, mock_client)
    mock_client.accept_negotiation.assert_not_called()
    mock_client.accept_negotiation_with_fund_address.assert_not_called()


@pytest.mark.anyio
async def test_worker_handle_order_paid(monkeypatch):
    from unittest.mock import MagicMock, AsyncMock
    from scripts.croo_provider_worker import handle_order_paid
    from bountyops.cap_adapter import LiveCapAdapter
    
    mock_sdk = MagicMock()
    mock_client = MagicMock()
    mock_sdk.AgentClient.return_value = mock_client
    mock_sdk.DeliverableType.SCHEMA = "schema"
    
    # Setup adapter
    adapter = LiveCapAdapter(mock_sdk, "key", "agent")
    adapter.client = mock_client
    
    # Mock return values for get_order
    class DummyOrder:
        def __init__(self, order_id, negotiation_id):
            self.order_id = order_id
            self.negotiation_id = negotiation_id
            self.requirements = None
            self.payload = None
            self.create_tx_hash = "0xCreateTx"
            self.pay_tx_hash = "0xPayTx"

    class DummyNegotiation:
        def __init__(self, negotiation_id, requirements):
            self.negotiation_id = negotiation_id
            self.requirements = requirements
            
    bad_order = DummyOrder(order_id="order_paid_123", negotiation_id="neg_paid_123")
    mock_negotiation = DummyNegotiation(
        negotiation_id="neg_paid_123",
        requirements=json.dumps({
            "opportunity_title": "Order Paid Negotiated Title",
            "opportunity_description": "Descr",
            "prize_pool_usd": 1000,
            "deadline": "2026-12-12",
            "builder_profile": "Name. Skills: Python. Goal: build"
        })
    )
    
    mock_client.get_order = AsyncMock(return_value=bad_order)
    mock_client.get_negotiation = AsyncMock(return_value=mock_negotiation)
    mock_client.deliver_order = AsyncMock()
    
    # Run the worker function
    await handle_order_paid({"id": "order_paid_123"}, adapter)
    
    mock_client.get_order.assert_called_once_with("order_paid_123")
    mock_client.get_negotiation.assert_called_once_with("neg_paid_123")
    mock_client.deliver_order.assert_called_once()
