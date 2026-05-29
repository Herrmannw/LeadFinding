from leadbot_worker.models.raw_record import ParsedSourceRecord
from leadbot_worker.pipeline.dedupe import dedupe_records


def test_dedupe_merges_same_phone_across_sources() -> None:
    records = [
        ParsedSourceRecord(
            source_name="yelp",
            source_url="https://www.yelp.com/biz/abc-heating",
            business_name="ABC Heating & Air LLC",
            phone="713-555-1234",
            city="Houston",
            state="TX",
            category="HVAC",
            review_count=34,
        ),
        ParsedSourceRecord(
            source_name="thumbtack",
            source_url="https://www.thumbtack.com/tx/houston/hvac/abc-heating/service",
            business_name="ABC Heating and Air",
            phone="(713) 555-1234",
            city="Houston",
            state="TX",
            category="HVAC",
        ),
    ]

    leads = dedupe_records(records)

    assert len(leads) == 1
    assert leads[0].phone == "7135551234"
    assert leads[0].source_count == 2
    assert leads[0].website_status == "no_website_found"


def test_dedupe_merges_similar_name_same_city() -> None:
    records = [
        ParsedSourceRecord(
            source_name="yelp",
            source_url="https://www.yelp.com/biz/lone-star-hvac",
            business_name="Lone Star HVAC",
            city="Houston",
            category="HVAC",
        ),
        ParsedSourceRecord(
            source_name="thumbtack",
            source_url="https://www.thumbtack.com/tx/houston/hvac/lone-star-hvac/service",
            business_name="Lone Star HVAC Services",
            city="Houston",
            category="HVAC",
        ),
    ]

    leads = dedupe_records(records)

    assert len(leads) == 1
    assert leads[0].dedupe_confidence is not None
    assert leads[0].dedupe_confidence >= 0.8
