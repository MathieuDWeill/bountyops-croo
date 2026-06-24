from __future__ import annotations

from .models import BuilderProfile, Opportunity


def scout_opportunity(opportunity: Opportunity, profile: BuilderProfile) -> dict:
    density = "unknown"
    if opportunity.buidls is not None:
        if opportunity.buidls <= 40:
            density = "low"
        elif opportunity.buidls <= 150:
            density = "medium"
        else:
            density = "high"

    missing = []
    req_text = " ".join(opportunity.requirements).lower()
    for required in ["github", "demo", "cap", "agent store", "open-source"]:
        if required not in req_text:
            missing.append(required)

    return {
        "title": opportunity.title,
        "platform": opportunity.platform,
        "prize_pool_usd": opportunity.prize_pool_usd,
        "days_left": opportunity.days_left,
        "competition_density": density,
        "visible_buidls": opportunity.buidls,
        "visible_hackers": opportunity.hackers,
        "requirements_detected": opportunity.requirements,
        "missing_requirement_signals": missing,
        "profile_fit_signals": [skill for skill in profile.skills if skill.lower() in " ".join(opportunity.tracks).lower() + opportunity.title.lower()],
    }
