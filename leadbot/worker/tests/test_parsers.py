from pathlib import Path

from leadbot_worker.pipeline.parse_records import parse_html

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text()


def test_parse_yelp_page_extracts_business_fields() -> None:
    record = parse_html(
        "yelp",
        fixture("yelp_profile.html"),
        "https://www.yelp.com/biz/abc-heating-and-air-houston",
        "site:yelp.com/biz HVAC Houston TX",
    )

    assert record.source_name == "yelp"
    assert record.source_url == "https://www.yelp.com/biz/abc-heating-and-air-houston"
    assert record.query_used == "site:yelp.com/biz HVAC Houston TX"
    assert record.business_name == "ABC Heating & Air LLC"
    assert record.phone == "7135551234"
    assert record.website_url == "https://abcheating.example"
    assert record.address == "100 Main St, Houston, TX 77002"
    assert record.city == "Houston"
    assert record.state == "TX"
    assert record.category == "HVAC Contractor"
    assert record.rating == 4.7
    assert record.review_count == 42
    assert record.profile_text == "ABC Heating & Air provides residential heating and AC repairs in Houston."
    assert record.parse_status == "parsed"
    assert record.parse_confidence is not None
    assert record.parse_confidence >= 0.9
    assert record.parser_version == "yelp_v1"
    assert record.raw_payload["json_ld_count"] >= 1
    assert record.raw_payload["website_link_found"] is True


def test_parse_thumbtack_page_extracts_business_fields() -> None:
    record = parse_html(
        "thumbtack",
        fixture("thumbtack_profile.html"),
        "https://www.thumbtack.com/tx/austin/hvac/lone-star/service",
    )

    assert record.source_name == "thumbtack"
    assert record.business_name == "Lone Star HVAC Services"
    assert record.phone == "5125550198"
    assert record.website_url is None
    assert record.address == "220 Congress Ave, Austin, TX 78701"
    assert record.city == "Austin"
    assert record.state == "TX"
    assert record.category == "Central Air Conditioning Repair"
    assert record.rating == 4.9
    assert record.review_count == 18
    assert record.parse_status == "parsed"
    assert record.parse_confidence is not None
    assert record.parse_confidence >= 0.8
    assert record.parser_version == "thumbtack_v1"
    assert record.raw_payload["website_link_found"] is False


def test_parser_returns_partial_record_for_unhelpful_html() -> None:
    record = parse_html("yelp", "<html><title>Access blocked</title></html>", "https://example.test")

    assert record.source_name == "yelp"
    assert record.source_url == "https://example.test"
    assert record.parse_status == "partial"
    assert record.error_message is None
    assert record.parse_confidence is not None
    assert record.parse_confidence < 0.5


def test_unknown_parser_fails_without_crashing() -> None:
    record = parse_html("unknown", "<html></html>", "https://example.test")

    assert record.parse_status == "failed"
    assert record.error_message == "No parser configured for source unknown"
