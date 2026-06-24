from __future__ import annotations

from .models import BuilderProfile, Opportunity
from .utils import clamp


def score_opportunity(opportunity: Opportunity, profile: BuilderProfile, scout: dict) -> dict:
    prize_score = clamp(opportunity.prize_pool_usd / 150)  # 10k ≈ 67
    if opportunity.prize_pool_usd >= 10000:
        prize_score += 10

    days = opportunity.days_left or 0
    urgency_score = 70 if 7 <= days <= 30 else 45 if days > 30 else 35

    density = scout.get("competition_density")
    density_score = {"low": 85, "medium": 60, "high": 35, "unknown": 50}.get(density, 50)

    track_text = " ".join(opportunity.tracks + opportunity.requirements + [opportunity.title]).lower()
    skill_hits = sum(1 for s in profile.skills if s.lower() in track_text)
    fit_score = clamp(70 + skill_hits * 10)

    effort_penalty = 0
    req_text = " ".join(opportunity.requirements).lower()
    for heavy in ["demo", "listed", "cap", "on-chain"]:
        if heavy in req_text:
            effort_penalty += 4
    if profile.time_budget_days < 3:
        effort_penalty += 15

    score = clamp(
        0.28 * prize_score
        + 0.18 * urgency_score
        + 0.24 * density_score
        + 0.25 * fit_score
        + 15
        - effort_penalty
    )

    if score >= 75:
        decision = "GO"
    elif score >= 55:
        decision = "GO"
    else:
        decision = "NO_GO"

    return {
        "expected_value_score": score,
        "decision": decision,
        "components": {
            "prize_score": clamp(prize_score),
            "urgency_score": urgency_score,
            "density_score": density_score,
            "fit_score": fit_score,
            "effort_penalty": effort_penalty,
        },
        "rationale": [
            f"Prize pool signal: ${opportunity.prize_pool_usd:,.0f}.",
            f"Competition density appears {density} based on visible BUIDLs.",
            f"Builder skill fit score is {fit_score}/100.",
            "The opportunity rewards callable, paid, composable agents, matching BountyOps' procurement workflow.",
        ],
    }
