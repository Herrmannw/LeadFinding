from leadbot_worker.models.lead import LeadCandidate
from leadbot_worker.models.raw_record import ParsedSourceRecord
from leadbot_worker.pipeline.score import score_lead


def test_score_high_priority_marketplace_business_without_website() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating and Air",
        normalized_name="abc heating and air",
        phone="7135551234",
        website_status="no_website_found",
        city="Houston",
        state="TX",
        category="HVAC",
        sources_found=["thumbtack", "yelp"],
        source_count=2,
        source_records=[
            ParsedSourceRecord(
                source_name="yelp",
                source_url="https://www.yelp.com/biz/abc-heating",
                review_count=42,
                profile_text="Residential heating and AC repairs.",
            ),
            ParsedSourceRecord(
                source_name="thumbtack",
                source_url="https://www.thumbtack.com/tx/houston/hvac/abc-heating/service",
            ),
        ],
    )

    score = score_lead(lead)

    assert score.alive_score >= 70
    assert score.no_website_score >= 70
    assert score.recommended_bucket == "high_priority"
    assert any("No official website" in reason for reason in score.score_reasons)


def test_score_penalizes_found_website() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating and Air",
        normalized_name="abc heating and air",
        phone="7135551234",
        website_url="abcheating.example",
        website_status="website_found",
        city="Houston",
        category="HVAC",
        sources_found=["yelp"],
        source_records=[
            ParsedSourceRecord(
                source_name="yelp",
                source_url="https://www.yelp.com/biz/abc-heating",
                review_count=4,
            )
        ],
    )

    score = score_lead(lead)

    assert score.no_website_score == 0
    assert score.recommended_bucket != "high_priority"


def test_score_treats_broken_or_parked_website_as_high_opportunity() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating and Air",
        normalized_name="abc heating and air",
        phone="7135551234",
        website_url="abcheating.example",
        website_status="broken_website",
        city="Houston",
        category="HVAC",
        sources_found=["thumbtack", "yelp"],
        source_records=[
            ParsedSourceRecord(
                source_name="yelp",
                source_url="https://www.yelp.com/biz/abc-heating",
                review_count=42,
                profile_text="Residential heating and AC repairs.",
            )
        ],
    )

    score = score_lead(lead)

    assert score.no_website_score >= 70
    assert score.recommended_bucket == "high_priority"
    assert any("broken or parked" in reason for reason in score.score_reasons)


def test_score_explains_unclear_website_status() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating and Air",
        website_status="unclear",
        sources_found=["yelp"],
    )

    score = score_lead(lead)

    assert score.no_website_score > 0
    assert any("needs review" in reason for reason in score.score_reasons)
