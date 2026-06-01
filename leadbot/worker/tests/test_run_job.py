from leadbot_worker.models.raw_record import ParsedSourceRecord, SourceUrl
from leadbot_worker.pipeline.collect_urls import MockSerpProvider, SourceUrlCollection
from leadbot_worker.pipeline.run_job import run_parse_pages_job, run_search_job, run_url_collection_job


def test_run_url_collection_job_logs_and_stores_discovered_urls(monkeypatch) -> None:
    events: list[tuple] = []

    def log_api_request(connection, **kwargs):
        events.append(("log", kwargs["query"], kwargs["success"], kwargs["metadata"]["source_name"]))

    def insert_raw_record(connection, search_job_id, record):
        events.append(
            (
                "insert",
                search_job_id,
                record.source_name,
                record.source_url,
                record.parse_status,
            )
        )
        return f"raw-{len(events)}"

    def update_job_progress(connection, job_id, **kwargs):
        events.append(("progress", job_id, kwargs))

    def mark_job_completed(connection, job_id, records_found, leads_created, qualified_leads):
        events.append(("completed", job_id, records_found, leads_created, qualified_leads))

    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.log_api_request", log_api_request)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.insert_raw_record", insert_raw_record)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.update_job_progress", update_job_progress)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.mark_job_completed", mark_job_completed)

    run_url_collection_job(
        object(),
        {
            "id": "job-1",
            "industry": "HVAC",
            "location": "Houston TX",
            "selected_sources": ["yelp", "thumbtack"],
            "target_record_count": 10,
        },
        MockSerpProvider(),
    )

    logged_sources = {event[3] for event in events if event[0] == "log"}
    inserted_urls = [event[3] for event in events if event[0] == "insert"]

    assert logged_sources == {"yelp", "thumbtack"}
    assert len(inserted_urls) == len(set(inserted_urls)) == 4
    assert all(event[4] == "needs_review" for event in events if event[0] == "insert")
    assert events[-1] == ("completed", "job-1", 4, 0, 0)


def test_run_parse_pages_job_fetches_and_stores_parsed_records(monkeypatch) -> None:
    events: list[tuple] = []

    def log_api_request(connection, **kwargs):
        events.append(("log", kwargs["metadata"]["source_name"]))

    def fetch_and_parse(source_url):
        return ParsedSourceRecord(
            source_name=source_url.source_name,
            source_url=str(source_url.url),
            query_used=source_url.query_used,
            business_name=f"Parsed {source_url.source_name}",
            parse_status="parsed",
            parse_confidence=0.9,
        )

    def insert_raw_record(connection, search_job_id, record):
        events.append(("insert", search_job_id, record.source_name, record.parse_status))
        return f"raw-{len(events)}"

    def update_job_progress(connection, job_id, **kwargs):
        events.append(("progress", job_id, kwargs))

    def mark_job_completed(connection, job_id, records_found, leads_created, qualified_leads):
        events.append(("completed", job_id, records_found, leads_created, qualified_leads))

    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.log_api_request", log_api_request)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.fetch_and_parse", fetch_and_parse)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.insert_raw_record", insert_raw_record)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.update_job_progress", update_job_progress)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.mark_job_completed", mark_job_completed)

    run_parse_pages_job(
        object(),
        {
            "id": "job-1",
            "industry": "HVAC",
            "location": "Houston TX",
            "selected_sources": ["yelp"],
            "target_record_count": 10,
        },
        MockSerpProvider(),
    )

    assert [event for event in events if event[0] == "insert"] == [
        ("insert", "job-1", "yelp", "parsed"),
        ("insert", "job-1", "yelp", "parsed"),
    ]
    assert events[-1] == ("completed", "job-1", 2, 0, 0)


def test_run_search_job_dedupes_and_preserves_source_evidence(monkeypatch) -> None:
    events: list[tuple] = []
    source_urls = [
        SourceUrl(
            source_name="yelp",
            url="https://www.yelp.com/biz/abc-heating",
            query_used="site:yelp.com/biz HVAC Houston TX",
        ),
        SourceUrl(
            source_name="thumbtack",
            url="https://www.thumbtack.com/tx/houston/hvac/abc-heating/service",
            query_used="site:thumbtack.com HVAC Houston TX",
        ),
    ]

    def collect_job_source_urls(job, provider):
        return SourceUrlCollection(urls=source_urls, request_logs=[])

    def fetch_and_parse(source_url):
        return ParsedSourceRecord(
            source_name=source_url.source_name,
            source_url=str(source_url.url),
            query_used=source_url.query_used,
            business_name="ABC Heating and Air",
            phone="+1 (713) 555-1234",
            city="Houston",
            state="TX",
            category="HVAC",
            review_count=42 if source_url.source_name == "yelp" else None,
            profile_text="Residential heating and AC repairs.",
        )

    def insert_raw_record(connection, search_job_id, record):
        return f"raw-{record.source_name}"

    def insert_lead_with_score(connection, search_job_id, lead, raw_record_ids, score):
        events.append(
            (
                "lead",
                search_job_id,
                lead.phone,
                lead.source_count,
                [record.source_name for record in lead.source_records],
                raw_record_ids,
                score.recommended_bucket,
            )
        )
        return "lead-1"

    def update_job_progress(connection, job_id, **kwargs):
        events.append(("progress", job_id, kwargs))

    def mark_job_completed(connection, job_id, records_found, leads_created, qualified_leads):
        events.append(("completed", job_id, records_found, leads_created, qualified_leads))

    monkeypatch.setattr(
        "leadbot_worker.pipeline.run_job.collect_job_source_urls",
        collect_job_source_urls,
    )
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.fetch_and_parse", fetch_and_parse)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.insert_raw_record", insert_raw_record)
    monkeypatch.setattr(
        "leadbot_worker.pipeline.run_job.queries.insert_lead_with_score",
        insert_lead_with_score,
    )
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.update_job_progress", update_job_progress)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.mark_job_completed", mark_job_completed)

    run_search_job(
        object(),
        {
            "id": "job-1",
            "industry": "HVAC",
            "location": "Houston TX",
            "selected_sources": ["yelp", "thumbtack"],
            "target_record_count": 10,
        },
        MockSerpProvider(),
    )

    assert events[2] == (
        "lead",
        "job-1",
        "7135551234",
        2,
        ["yelp", "thumbtack"],
        ["raw-yelp", "raw-thumbtack"],
        "high_priority",
    )
    assert events[-1] == ("completed", "job-1", 2, 1, 1)


def test_run_search_job_does_not_count_needs_review_leads_as_qualified(monkeypatch) -> None:
    events: list[tuple] = []
    source_urls = [
        SourceUrl(
            source_name="yelp",
            url="https://www.yelp.com/biz/northside-plumbing",
            query_used="site:yelp.com/biz Plumbing Austin TX",
        ),
        SourceUrl(
            source_name="thumbtack",
            url="https://www.thumbtack.com/tx/austin/plumbing/north-side/service",
            query_used="site:thumbtack.com Plumbing Austin TX",
        ),
    ]

    def collect_job_source_urls(job, provider):
        return SourceUrlCollection(urls=source_urls, request_logs=[])

    def fetch_and_parse(source_url):
        if source_url.source_name == "yelp":
            business_name = "Northside Plumbing"
            phone = "512-555-0101"
        else:
            business_name = "North Side Plumb"
            phone = "512-555-0102"
        return ParsedSourceRecord(
            source_name=source_url.source_name,
            source_url=str(source_url.url),
            query_used=source_url.query_used,
            business_name=business_name,
            phone=phone,
            city="Austin",
            state="TX",
            category="Plumbing",
            review_count=42,
            profile_text="Residential plumbing repairs.",
        )

    def insert_raw_record(connection, search_job_id, record):
        return f"raw-{record.source_name}"

    def insert_lead_with_score(connection, search_job_id, lead, raw_record_ids, score):
        events.append(("lead", lead.status, score.recommended_bucket))
        return f"lead-{len(events)}"

    def update_job_progress(connection, job_id, **kwargs):
        events.append(("progress", kwargs))

    def mark_job_completed(connection, job_id, records_found, leads_created, qualified_leads):
        events.append(("completed", records_found, leads_created, qualified_leads))

    monkeypatch.setattr(
        "leadbot_worker.pipeline.run_job.collect_job_source_urls",
        collect_job_source_urls,
    )
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.fetch_and_parse", fetch_and_parse)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.insert_raw_record", insert_raw_record)
    monkeypatch.setattr(
        "leadbot_worker.pipeline.run_job.queries.insert_lead_with_score",
        insert_lead_with_score,
    )
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.update_job_progress", update_job_progress)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.mark_job_completed", mark_job_completed)

    run_search_job(
        object(),
        {
            "id": "job-1",
            "industry": "Plumbing",
            "location": "Austin TX",
            "selected_sources": ["yelp", "thumbtack"],
            "target_record_count": 10,
        },
        MockSerpProvider(),
    )

    assert [event for event in events if event[0] == "lead"] == [
        ("lead", "needs_review", "high_priority"),
        ("lead", "needs_review", "high_priority"),
    ]
    assert events[-1] == ("completed", 2, 2, 0)
