import json
from pathlib import Path

from fastapi.testclient import TestClient

from bountyops.app import app

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
    assert data["sdk_available"] is False
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


