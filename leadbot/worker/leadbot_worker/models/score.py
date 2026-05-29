from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RecommendedBucket = Literal["high_priority", "review", "low_priority", "reject"]


class LeadScore(BaseModel):
    score_version: str = "v1"
    alive_score: int
    no_website_score: int
    opportunity_score: int
    score_reasons: list[str] = Field(default_factory=list)
    recommended_bucket: RecommendedBucket
