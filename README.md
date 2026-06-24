# BountyOps — Autonomous Opportunity-to-Submission Agent

**Find paid builder opportunities. Score expected value. Hire specialist agents. Produce a submission pack.**

BountyOps is a CAP-ready AI agent for the CROO Agent Hackathon. It helps builders turn fragmented hackathons, grants, bounties, and RFPs into monetizable action. A buyer agent can call BountyOps with a builder profile and an opportunity; BountyOps then orchestrates specialist agents to scout, score, design, write, and verify a complete submission package.

The first demo use case is the **CROO Agent Hackathon itself**: BountyOps evaluates the opportunity, selects the strongest project angle, hires specialist agents, and returns a verifiable submission pack.

## Why this matters

Builders waste time chasing low-ROI opportunities. BountyOps makes opportunity selection and submission preparation into an agent-commerce workflow:

```text
Builder / Buyer Agent
        ↓
BountyOps Orchestrator
        ↓
Scout Agent → ROI Scorer → Agent Designer → Submission Writer → Verifier
        ↓
Submission Pack + CAP Order Ledger + Proof Hash
```

This demonstrates CROO's core thesis: agents discover, hire, pay, verify, and compose other agents.

## Hackathon tracks

Primary track:

- **Open – Any A2A Agents** — BountyOps proves A2A composability by procuring work from multiple specialist agents.

Secondary track:

- **Developer Tooling Agents** — BountyOps helps builders decide what to build and prepares the assets required to submit.

## Features

- Opportunity ingestion from JSON, API payloads, or sample datasets.
- Expected-value scoring based on prize, deadline, competition density, requirements, effort, and builder fit.
- A2A orchestration across five specialist agents.
- CAP-style order lifecycle with quotes, paid orders, deliverables, settlement states, and a local mock ledger.
- Verifiable outputs with deterministic `proof_hash`.
- Generates:
  - go/no-go recommendation;
  - track selection;
  - project concept;
  - submission checklist;
  - DoraHacks writeup draft;
  - README outline;
  - 5-minute demo script;
  - risk and compliance review;
  - CAP-style order ledger.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn bountyops.app:app --reload
```

Open:

```text
http://localhost:8000/docs
```

Run the CROO demo scenario:

```bash
python -m bountyops.cli run examples/croo_input.json --out examples/bountyops_output.generated.json
```

Run tests:

```bash
pip install -r requirements-dev.txt
pytest -q
```

## API

### `GET /health`

Health check.

### `GET /capabilities`

Returns BountyOps services and pricing metadata.

### `POST /quote`

Returns a CAP-style quote for an opportunity-to-submission job.

### `POST /orders`

Creates a local CAP-style order.

### `POST /orders/{order_id}/pay`

Marks an order as paid and triggers the BountyOps orchestration.

### `GET /orders/{order_id}`

Returns the order, ledger state, and final deliverable if completed.

### `POST /run`

Runs the orchestration directly without the order lifecycle. Useful for local demos.

## Example request

```json
{
  "buyer_wallet": "0xBuyer0001",
  "builder_profile": {
    "name": "Mathieu",
    "skills": ["Python", "AI agents", "Kaggle", "Web3", "FastAPI"],
    "time_budget_days": 5,
    "goal": "maximize expected prize value while building something reusable"
  },
  "opportunity": {
    "title": "CROO Agent Hackathon",
    "platform": "DoraHacks / Kaggle",
    "prize_pool_usd": 10200,
    "deadline": "2026-07-12T11:00:00+02:00",
    "days_left": 18,
    "buidls": 33,
    "hackers": 184,
    "tracks": [
      "Research & Intelligence Agents",
      "Data & Verification Agents",
      "Creator & Content Ops Agents",
      "DeFi / On-chain Ops Agents",
      "Developer Tooling Agents",
      "Open – Any A2A Agents"
    ],
    "requirements": [
      "Listed on CROO Agent Store",
      "Integrated with CAP",
      "Open-source GitHub repo",
      "Demo video",
      "DoraHacks BUIDL filed"
    ]
  }
}
```

## Example output

```json
{
  "go_no_go": "GO",
  "expected_value_score": 86,
  "recommended_project": "BountyOps — Autonomous Opportunity-to-Submission Agent",
  "primary_track": "Open – Any A2A Agents",
  "secondary_track": "Developer Tooling Agents",
  "specialist_orders": [
    "Scout Agent",
    "ROI Scorer Agent",
    "Agent Designer Agent",
    "Submission Writer Agent",
    "Verifier Agent"
  ],
  "proof_hash": "sha256:..."
}
```

## CAP integration notes

This repo includes a local CAP adapter to make development and review reproducible without relying on a live chain. The adapter models the lifecycle expected from a paid callable agent:

1. Buyer requests a quote.
2. Buyer creates an order.
3. Buyer pays the order.
4. BountyOps hires specialist agents as counterparties.
5. Each specialist returns a deliverable.
6. BountyOps verifies and assembles the final pack.
7. The order is completed with a verifiable proof hash.

See [`docs/CAP_INTEGRATION.md`](docs/CAP_INTEGRATION.md).

## Live CROO runtime

BountyOps supports a production-grade live runtime using the official CROO Python SDK.

### Agent Store manual setup
Account setup, agent listing creation, service registration (e.g. `submission_pack`), and SDK API key generation are performed directly on the **[CROO Agent Store / Dashboard](https://agent.croo.network)**.

### Running mock mode (default)
Mock mode runs the local CAP adapter with in-memory order states and mock ledgers:
```bash
uvicorn bountyops.app:app --reload
```

### Running live mode
To run the server in live mode, ensure the official `croo-sdk` is installed, set `CAP_MODE=live`, and configure the API key and agent ID:
```bash
CAP_MODE=live \
CROO_API_URL=https://api.croo.network \
CROO_WS_URL=wss://api.croo.network/ws \
CROO_SDK_KEY=croo_sk_xxx \
CROO_AGENT_ID=agent_xxx \
BASE_RPC_URL=https://mainnet.base.org \
PYTHONPATH=src ./.venv/bin/uvicorn bountyops.app:app --reload
```

In live mode, you can use these endpoints to query the live CROO network:
- **List Paid Orders**: `GET /cap/live/orders?status=paid` (calls `list_orders` on the SDK)
- **Deliver Paid Order**: `POST /cap/live/deliver/{order_id}` (fetches order payload, runs the orchestrator, and uploads the schema deliverable with the `proof_hash`)
- **Process All Paid Orders**: `POST /cap/live/run-paid-orders`

### Running the worker daemon
For automated off-chain processing, you can start the background listener script. It connects to the CROO WebSocket, listens for `ORDER_PAID` events, runs the opportunity-to-submission workspace orchestration, and automatically delivers the submission pack:
```bash
CAP_MODE=live \
CROO_API_URL=https://api.croo.network \
CROO_WS_URL=wss://api.croo.network/ws \
CROO_SDK_KEY=croo_sk_xxx \
CROO_AGENT_ID=agent_xxx \
BASE_RPC_URL=https://mainnet.base.org \
./scripts/croo_provider_worker.py
```

## Project structure


```text
bountyops-croo/
├── src/bountyops/              # API, orchestrator, scoring, models, ledger
├── agents/                     # Specialist agent wrappers
├── data/                       # Sample opportunity data
├── examples/                   # CROO input/output examples
├── docs/                       # Demo script, writeup, CAP notes
├── tests/                      # Unit/API tests
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Monetization beyond the hackathon

BountyOps can be sold as:

- a paid opportunity scan for builders;
- a weekly high-ROI bounty alert agent;
- a submission-pack generator;
- a repo-to-opportunity matching service;
- a CAP-callable procurement desk for other agents.

Potential pricing:

- Opportunity scan: $5–$15.
- Full opportunity analysis: $25–$50.
- Submission pack: $99+.
- Recurring bounty intelligence: monthly subscription.

## License

MIT License.
