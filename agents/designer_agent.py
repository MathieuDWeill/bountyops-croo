"""Specialist agent wrapper used by the BountyOps local CAP demo.

In a live CROO deployment, each of these wrappers can become an independently
listed counterparty agent with its own wallet, pricing, and reputation.
"""

from __future__ import annotations


def describe() -> dict:
    return {
        "role": __name__.split(".")[-1],
        "mode": "local-demo",
        "note": "Replace this wrapper with a live CAP/CROO agent listing for production orders.",
    }
