# CAP Integration Notes

BountyOps is designed as a paid, callable agent that can be listed on CROO Agent Store.

## Local development mode

The repo includes `LocalCapAdapter`, which models a CAP-like lifecycle so the project is runnable without chain credentials:

1. `/quote` returns a price and deliverables.
2. `/orders` creates an order.
3. `/orders/{order_id}/pay` marks the order as paid.
4. BountyOps creates five specialist suborders.
5. Specialist agents deliver outputs.
6. BountyOps assembles a final submission pack.
7. The order is completed with a deterministic `proof_hash`.

## Live CAP migration plan

When CROO credentials are available:

- Replace `LocalCapAdapter.quote` with the CROO SDK quote/negotiation method.
- Replace `LocalCapAdapter.create_order` with live CAP order creation.
- Replace `pay_order` with order-paid event handling.
- Replace local specialist calls with real counterparty agent calls.
- Submit the final `SubmissionPack` as a typed deliverable.

## Counterparty agents

BountyOps is intentionally built around more than three unique counterparty agents:

- OpportunityScoutAgent
- ROIScorerAgent
- AgentDesignerAgent
- SubmissionWriterAgent
- VerifierAgent

This directly addresses the hackathon's A2A composability requirement and avoids the pattern of a single isolated endpoint.
