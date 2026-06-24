from __future__ import annotations

from .models import Opportunity


def verify_pack(opportunity: Opportunity, pack: dict, specialist_count: int) -> dict:
    issues = []
    req_text = " ".join(opportunity.requirements).lower()
    if "github" not in req_text and "git" not in req_text:
        issues.append("Repository requirement was not detected in opportunity metadata.")
    if "demo" not in req_text:
        issues.append("Demo video requirement was not detected in opportunity metadata.")
    if specialist_count < 3:
        issues.append("A2A risk: fewer than 3 unique counterparty agents.")
    if "proof" not in " ".join(pack.get("submission_checklist", [])).lower():
        issues.append("Verification artifact not emphasized in checklist.")

    if not issues:
        issues.append("No blocking issues detected for the local demo submission pack.")

    return {
        "passed": not any(i.startswith("A2A risk") for i in issues),
        "risk_review": issues,
        "next_actions": [
            "Replace local CAP adapter with live CROO SDK calls when credentials are available.",
            "List BountyOps on CROO Agent Store.",
            "Record a 3–5 minute demo using examples/croo_input.json.",
            "Create several test buyer wallets and counterparty agent listings for real order evidence.",
        ],
    }
