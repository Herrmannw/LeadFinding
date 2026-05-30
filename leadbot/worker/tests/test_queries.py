from leadbot_worker.db.queries import lead_status_for
from leadbot_worker.models.score import LeadScore


def test_lead_status_for_preserves_needs_review() -> None:
    score = LeadScore(
        alive_score=90,
        no_website_score=90,
        opportunity_score=90,
        recommended_bucket="high_priority",
    )

    assert lead_status_for(score, "needs_review") == "needs_review"


def test_lead_status_for_uses_score_for_new_leads() -> None:
    high_priority_score = LeadScore(
        alive_score=90,
        no_website_score=90,
        opportunity_score=90,
        recommended_bucket="high_priority",
    )
    reject_score = LeadScore(
        alive_score=10,
        no_website_score=10,
        opportunity_score=10,
        recommended_bucket="reject",
    )

    assert lead_status_for(high_priority_score) == "qualified"
    assert lead_status_for(reject_score) == "rejected"
