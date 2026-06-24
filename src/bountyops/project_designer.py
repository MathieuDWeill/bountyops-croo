from __future__ import annotations

from .models import BuilderProfile, Opportunity


def design_project(opportunity: Opportunity, profile: BuilderProfile, roi: dict) -> dict:
    tracks = opportunity.tracks
    primary = "Open – Any A2A Agents" if any("Open" in t for t in tracks) else (tracks[0] if tracks else "Open")
    secondary = "Developer Tooling Agents" if any("Developer" in t for t in tracks) else None

    return {
        "name": "BountyOps — Autonomous Opportunity-to-Submission Agent",
        "tagline": "Find paid builder opportunities, score expected value, and hire agents to prepare winning submissions.",
        "primary_track": primary,
        "secondary_track": secondary,
        "architecture": [
            "BountyOps orchestrator exposes CAP-callable services.",
            "Scout Agent extracts opportunity facts and constraints.",
            "ROI Scorer Agent evaluates expected value and go/no-go.",
            "Agent Designer Agent chooses the most commercially useful project angle.",
            "Submission Writer Agent produces the writeup, README outline, and demo script.",
            "Verifier Agent validates requirements and emits a proof hash.",
        ],
        "why_it_can_win": [
            "It demonstrates agents hiring agents rather than a standalone chatbot.",
            "It has clear monetization beyond the hackathon.",
            "It uses the hackathon itself as a memorable real-world demo.",
            "It naturally creates multiple counterparty agent orders.",
        ],
    }
