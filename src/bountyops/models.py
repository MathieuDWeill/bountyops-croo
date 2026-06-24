from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class OrderStatus(str, Enum):
    QUOTED = "quoted"
    CREATED = "created"
    PAID = "paid"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class BuilderProfile(BaseModel):
    name: str = "Builder"
    skills: list[str] = Field(default_factory=list)
    time_budget_days: int = 3
    goal: str = "maximize expected value"
    repo_url: HttpUrl | None = None


class Opportunity(BaseModel):
    title: str
    platform: str = "Unknown"
    url: HttpUrl | None = None
    prize_pool_usd: float = 0
    deadline: str | None = None
    days_left: int | None = None
    buidls: int | None = None
    hackers: int | None = None
    submissions: int | None = None
    tracks: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    judging_criteria: dict[str, float] = Field(default_factory=dict)
    notes: str | None = None


class RunRequest(BaseModel):
    buyer_wallet: str = "0xBuyerDemo"
    builder_profile: BuilderProfile
    opportunity: Opportunity
    requested_services: list[str] = Field(
        default_factory=lambda: [
            "opportunity_scan",
            "roi_ranking",
            "project_design",
            "submission_pack",
            "verification",
        ]
    )


class QuoteRequest(RunRequest):
    pass


class Quote(BaseModel):
    quote_id: str = Field(default_factory=lambda: f"quote_{uuid4().hex[:12]}")
    service: str = "opportunity_to_submission_pack"
    price_usdc: float = 25.0
    estimated_specialist_orders: int = 5
    expires_at: str
    deliverables: list[str]


class LedgerEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    actor: str
    action: str
    counterparty: str | None = None
    amount_usdc: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpecialistOrder(BaseModel):
    order_id: str = Field(default_factory=lambda: f"suborder_{uuid4().hex[:12]}")
    agent_name: str
    agent_wallet: str
    service: str
    price_usdc: float
    status: OrderStatus = OrderStatus.COMPLETED
    deliverable: dict[str, Any] = Field(default_factory=dict)


class SubmissionPack(BaseModel):
    go_no_go: Literal["GO", "NO_GO", "MAYBE"]
    expected_value_score: int
    recommended_project: str
    tagline: str
    primary_track: str
    secondary_track: str | None = None
    rationale: list[str]
    submission_checklist: list[str]
    readme_outline: str
    dorahacks_writeup: str
    demo_script: str
    risk_review: list[str]
    next_actions: list[str]


class RunResult(BaseModel):
    order_id: str
    buyer_wallet: str
    agent_name: str = "BountyOps"
    status: OrderStatus
    specialist_orders: list[SpecialistOrder]
    ledger: list[LedgerEvent]
    submission_pack: SubmissionPack
    proof_hash: str


class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: f"order_{uuid4().hex[:12]}")
    quote: Quote
    request: RunRequest
    status: OrderStatus = OrderStatus.CREATED
    result: RunResult | None = None
    ledger: list[LedgerEvent] = Field(default_factory=list)
