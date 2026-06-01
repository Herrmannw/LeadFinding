from leadbot_worker.models.lead import LeadCandidate
from leadbot_worker.models.raw_record import ParsedSourceRecord
from leadbot_worker.pipeline.website_presence import classify_website_status


def test_website_status_found_from_lead_website_url() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating",
        website_url="abcheating.example",
    )

    assert classify_website_status(lead) == "website_found"


def test_website_status_found_from_usable_source_record() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating",
        source_records=[
            ParsedSourceRecord(
                source_name="yelp",
                source_url="https://www.yelp.com/biz/abc-heating",
                website_url="https://abcheating.example",
                parse_status="parsed",
                parse_confidence=0.9,
            )
        ],
    )

    assert classify_website_status(lead) == "website_found"


def test_website_status_no_website_when_all_usable_records_have_no_website() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating",
        source_records=[
            ParsedSourceRecord(
                source_name="yelp",
                source_url="https://www.yelp.com/biz/abc-heating",
                parse_status="parsed",
                parse_confidence=0.9,
            ),
            ParsedSourceRecord(
                source_name="thumbtack",
                source_url="https://www.thumbtack.com/tx/houston/hvac/abc-heating/service",
                parse_status="partial",
                parse_confidence=0.7,
            ),
        ],
    )

    assert classify_website_status(lead) == "no_website_found"


def test_website_status_unknown_without_source_records() -> None:
    lead = LeadCandidate(canonical_name="ABC Heating")

    assert classify_website_status(lead) == "unknown"


def test_website_status_unknown_when_no_usable_records_exist() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating",
        source_records=[
            ParsedSourceRecord(
                source_name="yelp",
                source_url="https://www.yelp.com/biz/abc-heating",
                parse_status="failed",
                parse_confidence=0,
            ),
            ParsedSourceRecord(
                source_name="thumbtack",
                source_url="https://www.thumbtack.com/tx/houston/hvac/abc-heating/service",
                parse_status="needs_review",
                parse_confidence=0,
            ),
        ],
    )

    assert classify_website_status(lead) == "unknown"


def test_website_status_unclear_with_mixed_usable_and_unusable_records() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating",
        source_records=[
            ParsedSourceRecord(
                source_name="yelp",
                source_url="https://www.yelp.com/biz/abc-heating",
                parse_status="parsed",
                parse_confidence=0.9,
            ),
            ParsedSourceRecord(
                source_name="thumbtack",
                source_url="https://www.thumbtack.com/tx/houston/hvac/abc-heating/service",
                parse_status="failed",
                parse_confidence=0,
            ),
        ],
    )

    assert classify_website_status(lead) == "unclear"


def test_website_status_unclear_with_low_confidence_record_mixed_in() -> None:
    lead = LeadCandidate(
        canonical_name="ABC Heating",
        source_records=[
            ParsedSourceRecord(
                source_name="yelp",
                source_url="https://www.yelp.com/biz/abc-heating",
                parse_status="parsed",
                parse_confidence=0.9,
            ),
            ParsedSourceRecord(
                source_name="thumbtack",
                source_url="https://www.thumbtack.com/tx/houston/hvac/abc-heating/service",
                parse_status="partial",
                parse_confidence=0.3,
            ),
        ],
    )

    assert classify_website_status(lead) == "unclear"
