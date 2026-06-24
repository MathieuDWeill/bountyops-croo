import json
from pathlib import Path

from bountyops.models import RunRequest
from bountyops.orchestrator import run_bountyops


def test_croo_demo_go_decision():
    payload = json.loads(Path("examples/croo_input.json").read_text())
    result = run_bountyops(RunRequest(**payload))
    assert result.status == "completed"
    assert result.submission_pack.go_no_go in {"GO", "MAYBE"}
    assert result.submission_pack.expected_value_score >= 60
    assert len(result.specialist_orders) >= 5
    assert result.proof_hash.startswith("sha256:")


def test_unique_counterparty_agents():
    payload = json.loads(Path("examples/croo_input.json").read_text())
    result = run_bountyops(RunRequest(**payload))
    wallets = {order.agent_wallet for order in result.specialist_orders}
    assert len(wallets) >= 3
