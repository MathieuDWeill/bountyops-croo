from __future__ import annotations

from .models import BuilderProfile, Opportunity


def write_submission(opportunity: Opportunity, profile: BuilderProfile, design: dict, roi: dict) -> dict:
    name = design["name"]
    tagline = design["tagline"]

    readme_outline = f"""# {name}

{tagline}

## Problem
Paid builder opportunities are fragmented across hackathons, grants, bounties, and RFPs. Builders often waste time on low-ROI opportunities or miss undercrowded ones.

## Solution
BountyOps is a CAP-callable procurement agent. It scouts opportunities, scores expected value, then hires specialist agents to prepare a complete submission pack.

## A2A workflow
1. Buyer Agent requests an opportunity analysis.
2. BountyOps creates specialist orders.
3. Scout, ROI, Designer, Writer, and Verifier agents deliver their outputs.
4. BountyOps assembles a final pack with a proof hash.

## Monetization
BountyOps charges for opportunity scans, ROI rankings, and full submission packs.
"""

    writeup = f"""BountyOps is an autonomous bounty intelligence and submission desk for builders. It turns the CROO thesis into a concrete commercial workflow: a buyer agent pays BountyOps, and BountyOps hires specialist agents to transform a raw opportunity into a decision and submission pack.

For this demo, the opportunity is {opportunity.title}. BountyOps evaluates the prize pool, deadline, competition density, requirements, and builder fit. It recommends building BountyOps itself because the project directly proves A2A composability: agents discover, hire, pay, verify, and compose other agents.

The final deliverable includes a go/no-go recommendation, expected-value score, project concept, track selection, README outline, DoraHacks writeup, demo script, compliance checklist, CAP-style ledger, and proof hash.
"""

    demo_script = f"""0:00–0:30 — Introduce the problem: builders miss paid opportunities or waste time on low-ROI ones.
0:30–1:00 — Show the buyer agent submitting the {opportunity.title} opportunity to BountyOps.
1:00–1:45 — Show BountyOps creating specialist CAP-style orders for Scout, ROI Scorer, Designer, Writer, and Verifier agents.
1:45–2:45 — Show each specialist deliverable and the local CAP ledger with prices and counterparties.
2:45–3:45 — Show the final submission pack: go/no-go, expected-value score, recommended project, tracks, writeup, README, and demo script.
3:45–4:30 — Show the proof hash and verification checklist.
4:30–5:00 — Explain monetization beyond this hackathon: builders and agents can pay BountyOps to find and prepare profitable opportunities.
"""

    checklist = [
        "Public GitHub/GitLab/Bitbucket repository with MIT or Apache-2.0 license.",
        "CAP-callable service documented in README.",
        "CROO Agent Store listing prepared.",
        "Demo video under 5 minutes.",
        "DoraHacks BUIDL filed before deadline.",
        "At least three specialist counterparty agents shown in demo.",
        "Order ledger and proof hash included as verification artifacts.",
    ]

    return {
        "readme_outline": readme_outline,
        "dorahacks_writeup": writeup,
        "demo_script": demo_script,
        "submission_checklist": checklist,
    }
