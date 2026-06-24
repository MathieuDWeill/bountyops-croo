from __future__ import annotations

from .models import LedgerEvent


class Ledger:
    def __init__(self) -> None:
        self.events: list[LedgerEvent] = []

    def record(self, actor: str, action: str, counterparty: str | None = None, amount_usdc: float | None = None, **metadata):
        event = LedgerEvent(
            actor=actor,
            action=action,
            counterparty=counterparty,
            amount_usdc=amount_usdc,
            metadata=metadata,
        )
        self.events.append(event)
        return event
