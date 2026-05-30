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
            phone="+1 (713) 555-1234",
            city="Houston",
            state="TX",
            category="HVAC",
        ),
    ]

    leads = dedupe_records(records)

    assert len(leads) == 1
    assert leads[0].phone == "7135551234"
    assert leads[0].source_count == 2
    assert len(leads[0].source_records) == 2
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


def test_dedupe_merges_same_domain() -> None:
    records = [
        ParsedSourceRecord(
            source_name="yelp",
            source_url="https://www.yelp.com/biz/acme-air",
            business_name="Acme Air",
            website_url="https://www.acmeair.example/services",
        ),
        ParsedSourceRecord(
            source_name="thumbtack",
            source_url="https://www.thumbtack.com/tx/houston/hvac/acme-air/service",
            business_name="Acme Air Conditioning",
            website_url="www.acmeair.example",
        ),
    ]

    leads = dedupe_records(records)

    assert len(leads) == 1
    assert leads[0].website_url == "acmeair.example"
    assert leads[0].dedupe_key == "domain:acmeair.example"
    assert leads[0].website_status == "website_found"


def test_dedupe_merges_same_address() -> None:
    records = [
        ParsedSourceRecord(
            source_name="yelp",
            source_url="https://www.yelp.com/biz/abc-heating",
            business_name="ABC Heating",
            address="100 Main St, Houston, TX 77002",
        ),
        ParsedSourceRecord(
            source_name="thumbtack",
            source_url="https://www.thumbtack.com/tx/houston/hvac/abc-heating/service",
            business_name="ABC HVAC",
            address="100 Main St Houston TX 77002",
        ),
    ]

    leads = dedupe_records(records)

    assert len(leads) == 1
    assert leads[0].dedupe_key == "address:100 main st houston tx 77002"
    assert leads[0].dedupe_confidence == 0.9


def test_dedupe_does_not_fuzzy_merge_without_city() -> None:
    records = [
        ParsedSourceRecord(
            source_name="yelp",
            source_url="https://www.yelp.com/biz/lone-star-hvac",
            business_name="Lone Star HVAC",
            category="HVAC",
        ),
        ParsedSourceRecord(
            source_name="thumbtack",
            source_url="https://www.thumbtack.com/tx/houston/hvac/lone-star-hvac/service",
            business_name="Lone Star HVAC Services",
            category="HVAC",
        ),
    ]

    leads = dedupe_records(records)

    assert len(leads) == 2


def test_dedupe_keeps_possible_fuzzy_match_separate_for_review() -> None:
    records = [
        ParsedSourceRecord(
            source_name="yelp",
            source_url="https://www.yelp.com/biz/northside-plumbing",
            business_name="Northside Plumbing",
            city="Austin",
            category="Plumbing",
        ),
        ParsedSourceRecord(
            source_name="thumbtack",
            source_url="https://www.thumbtack.com/tx/austin/plumbing/north-side/service",
            business_name="North Side Plumb",
            city="Austin",
            category="Plumbing",
        ),
    ]

    leads = dedupe_records(records)

    assert len(leads) == 2
    assert {lead.status for lead in leads} == {"needs_review"}
    assert {lead.dedupe_confidence for lead in leads} == {0.65}


def test_dedupe_promotes_stronger_key_after_fuzzy_merge() -> None:
    records = [
        ParsedSourceRecord(
            source_name="yelp",
            source_url="https://www.yelp.com/biz/abc-heating",
            business_name="ABC Heating",
            city="Houston",
            category="HVAC",
        ),
        ParsedSourceRecord(
            source_name="thumbtack",
            source_url="https://www.thumbtack.com/tx/houston/hvac/abc-heating/service",
            business_name="ABC Heating and Air",
            phone="+1 (713) 555-1234",
            city="Houston",
            category="HVAC",
        ),
    ]

    leads = dedupe_records(records)

    assert len(leads) == 1
    assert leads[0].phone == "7135551234"
    assert leads[0].dedupe_key == "phone:7135551234"
