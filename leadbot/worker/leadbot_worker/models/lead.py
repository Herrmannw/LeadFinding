from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from leadbot_worker.models.raw_record import ParsedSourceRecord

WebsiteStatus = Literal[
    "unknown",
    "no_website_found",
    "website_found",
    "broken_website",
    "parked_domain",
    "unclear",
]

LeadStatus = Literal["new", "qualified", "needs_review", "duplicate", "rejected", "dead"]


@dataclass(slots=True)
class LeadCandidate:
    canonical_name: str
    normalized_name: str | None = None
    phone: str | None = None
    website_url: str | None = None
    website_status: WebsiteStatus = "unknown"
    address: str | None = None
    city: str | None = None
    state: str | None = None
    category: str | None = None
    sources_found: list[str] = field(default_factory=list)
    source_count: int = 0
    best_source_url: str | None = None
    status: LeadStatus = "new"
    dedupe_key: str | None = None
    dedupe_confidence: float | None = None
    source_records: list[ParsedSourceRecord] = field(default_factory=list)
