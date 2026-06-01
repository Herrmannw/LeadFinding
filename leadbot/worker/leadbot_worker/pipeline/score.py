from __future__ import annotations

from leadbot_worker.models.lead import LeadCandidate
from leadbot_worker.models.score import LeadScore, RecommendedBucket

SCORE_VERSION = "v1"


def score_lead(lead: LeadCandidate) -> LeadScore:
    reasons: list[str] = []
    source_names = set(lead.sources_found)

    alive_score = 0
    if "thumbtack" in source_names:
        alive_score += 30
        reasons.append("Appears on Thumbtack")
    if "yelp" in source_names:
        alive_score += 25
        reasons.append("Appears on Yelp")
    if len(source_names) >= 2:
        alive_score += 10
        reasons.append("Appears on multiple sources")
    if lead.phone:
        alive_score += 15
        reasons.append("Phone number found")

    max_reviews = max((record.review_count or 0 for record in lead.source_records), default=0)
    if max_reviews >= 20:
        alive_score += 20
        reasons.append(f"Marketplace profile has {max_reviews} reviews")
    elif max_reviews > 0:
        alive_score += 10
        reasons.append("Marketplace profile has reviews")

    if any(record.profile_text for record in lead.source_records):
        alive_score += 10
        reasons.append("Profile includes business description")

    if not lead.phone and max_reviews == 0:
        alive_score -= 30
        reasons.append("No phone number or review activity found")

    no_website_score = 0
    if lead.website_status == "no_website_found":
        no_website_score += 65
        reasons.append("No official website found on source profiles")
    elif lead.website_status == "website_found":
        no_website_score -= 50
        reasons.append("Official website found")
    elif lead.website_status in {"broken_website", "parked_domain"}:
        no_website_score += 75
        reasons.append("Website appears broken or parked")
    elif lead.website_status == "unknown":
        no_website_score += 20
        reasons.append("Website status is still unknown")
    elif lead.website_status == "unclear":
        no_website_score += 10
        reasons.append("Website status needs review")

    if len(source_names) >= 1 and not lead.website_url:
        no_website_score += 10
        reasons.append("Marketplace profile may be primary web presence")

    category_value = 50 if lead.category else 30
    opportunity_score = round(alive_score * 0.5 + no_website_score * 0.4 + category_value * 0.1)

    alive_score = clamp(alive_score)
    no_website_score = clamp(no_website_score)
    opportunity_score = clamp(opportunity_score)

    bucket = bucket_for(alive_score, no_website_score)

    return LeadScore(
        score_version=SCORE_VERSION,
        alive_score=alive_score,
        no_website_score=no_website_score,
        opportunity_score=opportunity_score,
        score_reasons=reasons,
        recommended_bucket=bucket,
    )


def clamp(value: int) -> int:
    return max(0, min(100, value))


def bucket_for(alive_score: int, no_website_score: int) -> RecommendedBucket:
    if alive_score >= 70 and no_website_score >= 70:
        return "high_priority"
    if alive_score >= 50 and no_website_score >= 50:
        return "review"
    if alive_score >= 40:
        return "low_priority"
    return "reject"
