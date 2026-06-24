from __future__ import annotations

from .ledger import Ledger
from .models import OrderStatus, RunRequest, RunResult, SpecialistOrder, SubmissionPack
from .opportunity_scout import scout_opportunity
from .project_designer import design_project
from .roi_scorer import score_opportunity
from .submission_writer import write_submission
from .utils import canonical_hash
from .verifier import verify_pack

SPECIALISTS = [
    ("OpportunityScoutAgent", "0xScoutAgent", "opportunity_scan", 2.00),
    ("ROIScorerAgent", "0xROIScorer", "expected_value_scoring", 3.00),
    ("AgentDesignerAgent", "0xDesignerAgent", "project_design", 4.00),
    ("SubmissionWriterAgent", "0xWriterAgent", "submission_pack_drafting", 8.00),
    ("VerifierAgent", "0xVerifierAgent", "compliance_and_proof_check", 3.00),
]


def run_bountyops(request: RunRequest, order_id: str = "order_local_demo") -> RunResult:
    ledger = Ledger()
    ledger.record("Buyer", "order_paid", counterparty="BountyOps", amount_usdc=25.0, buyer_wallet=request.buyer_wallet)
    ledger.record("BountyOps", "orchestration_started", opportunity=request.opportunity.title)

    specialist_orders: list[SpecialistOrder] = []

    scout = scout_opportunity(request.opportunity, request.builder_profile)
    specialist_orders.append(_make_order(0, scout))
    ledger.record("BountyOps", "specialist_paid", counterparty="OpportunityScoutAgent", amount_usdc=2.0)

    roi = score_opportunity(request.opportunity, request.builder_profile, scout)
    specialist_orders.append(_make_order(1, roi))
    ledger.record("BountyOps", "specialist_paid", counterparty="ROIScorerAgent", amount_usdc=3.0)

    design = design_project(request.opportunity, request.builder_profile, roi)
    specialist_orders.append(_make_order(2, design))
    ledger.record("BountyOps", "specialist_paid", counterparty="AgentDesignerAgent", amount_usdc=4.0)

    writing = write_submission(request.opportunity, request.builder_profile, design, roi)
    specialist_orders.append(_make_order(3, writing))
    ledger.record("BountyOps", "specialist_paid", counterparty="SubmissionWriterAgent", amount_usdc=8.0)

    verification = verify_pack(request.opportunity, writing, specialist_count=len(SPECIALISTS))
    specialist_orders.append(_make_order(4, verification))
    ledger.record("BountyOps", "specialist_paid", counterparty="VerifierAgent", amount_usdc=3.0)

    pack = SubmissionPack(
        go_no_go=roi["decision"],
        expected_value_score=roi["expected_value_score"],
        recommended_project=design["name"],
        tagline=design["tagline"],
        primary_track=design["primary_track"],
        secondary_track=design.get("secondary_track"),
        rationale=roi["rationale"] + design["why_it_can_win"],
        submission_checklist=writing["submission_checklist"],
        readme_outline=writing["readme_outline"],
        dorahacks_writeup=writing["dorahacks_writeup"],
        demo_script=writing["demo_script"],
        risk_review=verification["risk_review"],
        next_actions=verification["next_actions"],
    )
    proof_hash = canonical_hash({
        "request": request.model_dump(mode="json"),
        "specialist_orders": [o.model_dump(mode="json") for o in specialist_orders],
        "submission_pack": pack.model_dump(mode="json"),
    })
    ledger.record("BountyOps", "final_deliverable_created", proof_hash=proof_hash)
    ledger.record("BountyOps", "order_completed", counterparty="Buyer", amount_usdc=25.0)

    return RunResult(
        order_id=order_id,
        buyer_wallet=request.buyer_wallet,
        status=OrderStatus.COMPLETED,
        specialist_orders=specialist_orders,
        ledger=ledger.events,
        submission_pack=pack,
        proof_hash=proof_hash,
    )


def _make_order(index: int, deliverable: dict) -> SpecialistOrder:
    name, wallet, service, price = SPECIALISTS[index]
    return SpecialistOrder(
        agent_name=name,
        agent_wallet=wallet,
        service=service,
        price_usdc=price,
        deliverable=deliverable,
    )
